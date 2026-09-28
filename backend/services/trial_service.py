"""Free-trial quota for YouTube analyses.

Two operations, both defined here so the arithmetic lives in exactly one place:

- `decrement_trial_use` — the *only* gate that matters. It runs the conditional
  UPDATE inside the caller's transaction, so the consume and the job INSERT commit
  together or not at all. The count the dependency checked earlier is advisory.
- `refund_trial_use` — gives a use back when a job fails. Idempotent, because the
  pipeline handler and the boot sweeper can race on the same job.
"""
from sqlalchemy import select, update

from backend.database import async_session
from backend.models import AnalysisJob, User


class TrialExhausted(Exception):
    """Raised when the atomic consume finds no uses left.

    Callers translate this to a 402. It is raised from inside `create_job`'s
    transaction, so the job row is never created — there is nothing to refund.
    """


async def decrement_trial_use(session, user_id: str) -> int:
    """Consume one free-trial use and return the remaining count.

    MUST be passed the caller's open session so that this UPDATE and the job INSERT
    it belongs to land in the same transaction. That single transaction is the
    serialization point: two tabs that both saw "1 left" cannot both succeed,
    because the second UPDATE matches no row once the first has committed.

    Raises TrialExhausted when the account has none left — either 0 uses, or NULL
    (no trial at all).
    """
    result = await session.execute(
        update(User)
        .where(User.id == user_id)
        .where(User.trial_uses_remaining > 0)
        .values(trial_uses_remaining=User.trial_uses_remaining - 1)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount == 0:
        raise TrialExhausted("No free-trial uses remaining")

    # Read the new value back through the same transaction, rather than trusting a
    # possibly-stale ORM attribute.
    remaining = await session.scalar(
        select(User.trial_uses_remaining).where(User.id == user_id)
    )
    return remaining


async def refund_trial_use(job_id: str) -> bool:
    """Return the free-trial use a job consumed. True if a use was credited.

    Idempotent by claiming the job's `trial_use_consumed` flag first: read the flag,
    clear it and credit the account inside one transaction, gated on the flag still
    being set. The pipeline's failure handler and the boot sweeper therefore cannot
    both refund the same job — whichever runs second sees the flag already cleared.

    Returns False for Rumble rows (flag never set) and for jobs that failed normally.
    """
    async with async_session() as session:
        job = await session.get(AnalysisJob, job_id)
        if job is None or not job.trial_use_consumed or not job.user_id:
            return False

        owner_id = job.user_id

        # The claim. A concurrent refund that already cleared the flag leaves this
        # matching no row, and we bail without crediting twice.
        claimed = await session.execute(
            update(AnalysisJob)
            .where(AnalysisJob.id == job_id)
            .where(AnalysisJob.trial_use_consumed.is_(True))
            .values(trial_use_consumed=False)
            .execution_options(synchronize_session=False)
        )
        if claimed.rowcount == 0:
            return False

        # Only credit accounts that actually have a trial: `trial_uses_remaining`
        # NULL means "no trial", and incrementing it would turn NULL into 1.
        await session.execute(
            update(User)
            .where(User.id == owner_id)
            .where(User.trial_uses_remaining.isnot(None))
            .values(trial_uses_remaining=User.trial_uses_remaining + 1)
            .execution_options(synchronize_session=False)
        )
        await session.commit()
        return True

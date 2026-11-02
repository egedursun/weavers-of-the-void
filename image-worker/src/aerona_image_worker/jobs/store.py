from collections import OrderedDict

from aerona_image_worker.errors import JobNotFoundError
from aerona_image_worker.jobs.job import Job


class JobStore:
    def __init__(self, retained: int) -> None:
        self._retained = retained
        self._jobs: OrderedDict[str, Job] = OrderedDict()

    def add(self, job: Job) -> None:
        self._jobs[job.job_id] = job
        self.prune()

    def get(self, job_id: str) -> Job:
        job = self._jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(f"image job {job_id} does not exist")
        return job

    def prune(self) -> None:
        finished = [job_id for job_id, job in self._jobs.items() if job.finished]
        for job_id in finished[: max(0, len(finished) - self._retained)]:
            del self._jobs[job_id]

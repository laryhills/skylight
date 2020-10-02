import redis
from rq import Queue
from rq.job import Job, NoSuchJobError

from sms.config import db, ma, redis_conn


class User(db.Model):
    username = db.Column(db.Text, primary_key=True, nullable=False)
    password = db.Column(db.Text, nullable=False)
    permissions = db.Column(db.Text, nullable=False)
    title = db.Column(db.Text, unique=True, nullable=False)
    fullname = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    def get_queue(self):
        return Queue(self.username + '-sheet-gen', connection=redis_conn)

    def queue_task(self, name, func, *args, **kwargs):
        queue = self.get_queue()
        job = queue.enqueue(func, *args, **kwargs)
        job_id = job.get_id()
        task = Task(id=job_id, name=name, user=self, status=job.get_status())
        db.session.add(task)
        db.session.commit()

        return job_id


class Task(db.Model):
    id = db.Column(db.String, primary_key=True, nullable=False)
    name = db.Column(db.String, nullable=False)
    username = db.Column(db.Text, db.ForeignKey('user.username'))
    status = db.Column(db.String, nullable=False)

    def get_rq_job(self):
        try:
            job = Job(id=self.id, connection=redis_conn)
        except (redis.exceptions.RedisError, NoSuchJobError):
            return None
        return job

    @staticmethod
    def get_name(job_id):
        return Task.query.filter_by(id=job_id).first().name


class UserSchema(ma.ModelSchema):
    class Meta:
        model = User
        sqla_session = db.session
        exclude = ['tasks']

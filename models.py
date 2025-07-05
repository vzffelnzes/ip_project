from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from database import Base


class BadWords(Base):
	__tablename__ = 'bad_words'
	id = Column(Integer, primary_key=True, index=True)
	word = Column(String, unique=True, nullable=False)
	group_id = Column(String, ForeignKey('groups.group_id'))

	group = relationship('Group', back_populates='bad_words')


class GroupSettings(Base):
	__tablename__ = 'chat_settings'

	group_id = Column(String, ForeignKey('groups.group_id'), primary_key=True)
	language = Column(String(10), default='en')
	is_censorship_enabled = Column(Boolean, default=True)
	is_auto_punishment_enabled = Column(Boolean, default=True)
	max_message_length = Column(Integer, default=1000)

	group = relationship('Group', back_populates='settings')


class GroupSubscription(Base):
	__tablename__ = 'chat_subscriptions'

	group_id = Column(String, ForeignKey('groups.group_id'), primary_key=True)
	expires_at = Column(DateTime, nullable=False)  # Дата окончания подписки
	is_premium = Column(Boolean, default=False)  # Премиум ли чат

	group = relationship('Group', back_populates='subscription')


class ViolationRule(Base):
	__tablename__ = 'violation_rules'

	id = Column(Integer, primary_key=True)
	group_id = Column(String, ForeignKey('groups.group_id'), nullable=False)
	violation_count = Column(Integer, nullable=False)  # Например: 2, 5, 10
	action_type = Column(String(20), nullable=False)  # warn / mute / ban
	mute_duration_sec = Column(Integer, default=600)  # Если action_type == mute

	group = relationship('Group', back_populates='violation_rules')


class UserViolation(Base):
	__tablename__ = 'user_violations'

	id = Column(Integer, primary_key=True)
	group_id = Column(String, ForeignKey('groups.group_id'))
	user_id = Column(BigInteger, nullable=False)
	count = Column(Integer, default=0)
	last_violation_time = Column(DateTime, default=func.now())

	group = relationship('Group', back_populates='user_violations')


class Group(Base):
	__tablename__ = 'groups'

	id = Column(Integer, primary_key=True, index=True)
	group_id = Column(String, unique=True)
	owner_id = Column(BigInteger)

	settings = relationship('GroupSettings', back_populates='group', uselist=False)
	bad_words = relationship('BadWords', back_populates='group')
	user_violations = relationship('UserViolation', back_populates='group')
	violation_rules = relationship('ViolationRule', back_populates='group')
	subscription = relationship('GroupSubscription', back_populates='group', uselist=False)

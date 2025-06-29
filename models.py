from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


class BadWords(Base):
	__tablename__ = 'bad_words'
	id = Column(Integer, primary_key=True, index=True)
	word = Column(String, unique=True, nullable=False)
	group_id = Column(Integer, ForeignKey('groups.id'))

	group = relationship('Group', back_populates='bad_words')


class Group(Base):
	__tablename__ = 'groups'
	id = Column(Integer, primary_key=True, index=True)
	group_id = Column(String, unique=True)
	owner_id = Column(BigInteger)
	is_active = Column(Boolean, default=False)
	pay_date = Column(DateTime)
	bad_words = relationship('BadWords', back_populates='group', cascade='all, delete-orphan')

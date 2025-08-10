from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'User'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    email = Column(String(255), unique=True)
    password = Column(String(255))
    role = Column(Text, default="A-Team")  # ✅ fixed default string

    assignments = relationship("FtaAssignments", back_populates="assigned_by_user")


class FtaAssignments(Base):
    __tablename__ = 'fta_assignments'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    fta_id = Column(String(50), unique=True)
    assigned_to = Column(String(255))
    assigned_by = Column(Integer, ForeignKey("User.id"))
    assigned_at = Column(DateTime)  # ✅ changed from Text to DateTime

    assigned_by_user = relationship("User", back_populates="assignments")
    responses = relationship("FtaResponses", back_populates="assignment")
    submissions = relationship("FtaSubmissions", back_populates="assignment")


class FtaSubmissions(Base):
    __tablename__ = 'fta_submissions'
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255))
    phone = Column(String(20))  # ✅ Changed from Integer to String
    invited_by = Column(String(255))
    mg_date = Column(DateTime)  # ✅ DateTime instead of Text
    met_date = Column(DateTime)
    location = Column(String(255))
    invited_person_role = Column(String(100))
    comments = Column(Text)
    submitted_at = Column(DateTime)
    fta_id = Column(String(50), ForeignKey("fta_assignments.fta_id"))

    assignment = relationship("FtaAssignments", back_populates="submissions")


class FtaResponses(Base):
    __tablename__ = 'fta_responses'
    id = Column(Integer, primary_key=True, autoincrement=True)  # ✅ Added primary key
    Timestamp = Column(DateTime)  # ✅ Changed from Text to DateTime
    Email_address = Column(String(255))
    Full_Name = Column(String(255))
    Phone_number = Column(String(20))  # ✅ Changed from Integer to String
    Gender = Column(String(20))
    Home_Address = Column(Text)
    Service_Experience = Column(Integer)
    Worship_Experience = Column(Integer)
    Word_Experience = Column(Float)
    General_Feedback = Column(Text)
    Invited_By = Column(String(255))
    Membership_Interest = Column(String(100))
    Consent = Column(String(100))
    Meeting_Date = Column(DateTime)  # ✅ DateTime
    FTA_ID = Column(String(50), ForeignKey("fta_assignments.fta_id"))

    assignment = relationship("FtaAssignments", back_populates="responses")


class Feedback(Base):
    __tablename__ = 'fta_feedback'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255))  # Email of the team member submitting the feedback
    fta_id = Column(String(50))  # ID of the FTA the feedback is about
    call_type = Column(String(100))  # e.g. "1st call", "2nd call"
    call_success = Column(String(255))  # Success status of the call
    feedback_1 = Column(Text)  # Specific feedback from first call
    met_date = Column(DateTime, nullable=True)  # When they met
    mg_date = Column(DateTime, nullable=True)  # Meet & Greet date
    department = Column(String(255), nullable=True)  # Department handed over to
    general_feedback = Column(Text, nullable=True)  # Overall notes
    submitted_at = Column(DateTime)  # When the feedback was submitted

class EmailLogs(Base):
    __tablename__ = 'email_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fta_id = Column(String(50))  # ID of the FTA the email was about
    fta_name = Column(String(255))  # Name of the FTA
    email = Column(String(255))  # Hashed email address
    subject = Column(String(255))  # Subject of the email
    status = Column(String(50))  # e.g., "sent", "failed"
    error_message = Column(Text, nullable=True)  # Error message if any
    timestamp = Column(DateTime)  # When the email was logged


class ATeamMember(Base):
    __tablename__ = "a_team_members"

    email = Column(String, primary_key=True)
    full_name = Column(String)


class AssignmentTracker(Base):
    __tablename__ = "assignment_tracker"

    id = Column(Integer, primary_key=True)
    last_assigned_index = Column(Integer)
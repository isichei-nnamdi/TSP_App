# API Reference

## Database Functions Reference

### Authentication Functions

#### `authenticate_user(email: str, password: str) -> Optional[User]`
Authenticates a user and returns user object if credentials are valid.

**Parameters:**
- `email` (str): User email address
- `password` (str): Plain text password to verify

**Returns:**
- `User`: User object if authentication succeeds
- `None`: If authentication fails

**Raises:**
- `ValueError`: If email or password is empty

**Example:**
```python
from db import authenticate_user

user = authenticate_user("john@example.com", "password123")
if user:
    st.success(f"Welcome {user.name}!")
else:
    st.error("Invalid credentials")
```

---

#### `hash_password(password: str) -> str`
Hashes a plaintext password using bcrypt.

**Parameters:**
- `password` (str): Plain text password

**Returns:**
- `str`: Hashed password

**Example:**
```python
from db import hash_password

hashed = hash_password("mysecurepassword")
# Use in user creation
```

---

### FTA Functions

#### `get_existing_assignments() -> List[FtaAssignments]`
Retrieves all existing FTA assignments from database.

**Returns:**
- `List[FtaAssignments]`: List of all assignments

**Example:**
```python
from db import get_existing_assignments

assignments = get_existing_assignments()
for assignment in assignments:
    print(f"{assignment.name} assigned to {assignment.assigned_to}")
```

---

#### `sync_and_assign_fta_responses(gsheet_url: str) -> List[FtaResponses]`
Syncs FTA responses from Google Sheets and assigns them using round-robin.

**Parameters:**
- `gsheet_url` (str): URL of Google Sheet containing FTA data

**Returns:**
- `List[FtaResponses]`: List of synced FTA responses

**Raises:**
- `Exception`: If Google Sheets cannot be accessed

**Note:** This function uses round-robin assignment to distribute FTAs evenly among team members.

**Example:**
```python
from db import sync_and_assign_fta_responses

gsheet_url = st.secrets["secrets"]["gsheet_url"]
responses = sync_and_assign_fta_responses(gsheet_url)
st.write(f"Synced {len(responses)} FTA responses")
```

---

#### `sync_a_team_members() -> None`
Synchronizes A-Team member data from external source.

**Example:**
```python
from db import sync_a_team_members

sync_a_team_members()
```

---

#### `get_fta_by_id(fta_id: str) -> Optional[FtaResponses]`
Retrieves a specific FTA response by ID.

**Parameters:**
- `fta_id` (str): Unique FTA identifier

**Returns:**
- `FtaResponses`: FTA response object
- `None`: If FTA not found

**Example:**
```python
from db import get_fta_by_id

fta = get_fta_by_id("FTA001")
if fta:
    st.write(f"Name: {fta.Full_Name}, Email: {fta.Email_address}")
```

---

### User Management Functions

#### `create_user(name: str, email: str, password: str, role: str) -> User`
Creates a new user account.

**Parameters:**
- `name` (str): User's full name
- `email` (str): User's email address
- `password` (str): Plain text password
- `role` (str): User role ("A-Team" or "Admin")

**Returns:**
- `User`: Newly created user object

**Raises:**
- `ValueError`: If email already exists
- `ValueError`: If email format invalid

**Example:**
```python
from db import create_user

new_user = create_user(
    name="John Doe",
    email="john@example.com",
    password="secure123",
    role="A-Team"
)
st.success(f"User {new_user.name} created")
```

---

#### `get_user_by_email(email: str) -> Optional[User]`
Retrieves user by email address.

**Parameters:**
- `email` (str): User email

**Returns:**
- `User`: User object
- `None`: If user not found

**Example:**
```python
from db import get_user_by_email

user = get_user_by_email("john@example.com")
if user:
    st.write(f"User role: {user.role}")
```

---

#### `get_all_users() -> List[User]`
Retrieves all users from database.

**Returns:**
- `List[User]`: All user objects

**Example:**
```python
from db import get_all_users

users = get_all_users()
user_names = [u.name for u in users]
st.write(f"Users: {', '.join(user_names)}")
```

---

#### `update_user(user_id: int, **kwargs) -> User`
Updates user information.

**Parameters:**
- `user_id` (int): User ID
- `**kwargs`: Fields to update (name, email, role, etc.)

**Returns:**
- `User`: Updated user object

**Example:**
```python
from db import update_user

updated_user = update_user(1, name="Jane Doe", role="Admin")
```

---

#### `delete_user(user_id: int) -> bool`
Deletes a user account.

**Parameters:**
- `user_id` (int): User ID to delete

**Returns:**
- `True`: If deletion successful
- `False`: If user not found

**Example:**
```python
from db import delete_user

if delete_user(user_id=5):
    st.success("User deleted")
else:
    st.error("User not found")
```

---

### FTA Submission & Feedback Functions

#### `add_fta_submission(fta_id: str, submission_data: dict) -> FtaSubmissions`
Records an FTA submission with follow-up details.

**Parameters:**
- `fta_id` (str): FTA identifier
- `submission_data` (dict): Submission details
  - `full_name` (str): FTA full name
  - `phone` (str): Phone number
  - `invited_by` (str): Who invited them
  - `mg_date` (datetime): Meet & Greet date
  - `met_date` (datetime): Met date
  - `location` (str): Location
  - `comments` (str): Additional comments

**Returns:**
- `FtaSubmissions`: Created submission object

**Example:**
```python
from db import add_fta_submission
from datetime import datetime

submission = add_fta_submission(
    fta_id="FTA001",
    submission_data={
        'full_name': 'John Doe',
        'phone': '555-1234',
        'invited_by': 'Jane Smith',
        'mg_date': datetime.now(),
        'location': 'Church Building',
        'comments': 'Great attendance!'
    }
)
```

---

#### `add_feedback(fta_id: str, feedback_data: dict) -> Feedback`
Records feedback from team member interaction with FTA.

**Parameters:**
- `fta_id` (str): FTA identifier
- `feedback_data` (dict): Feedback details
  - `email` (str): Team member email
  - `call_type` (str): Type of call (1st call, 2nd call, etc.)
  - `call_success` (str): Success status
  - `feedback_1` (str): Detailed feedback
  - `met_date` (datetime): Meeting date
  - `mg_date` (datetime): Meet & Greet date
  - `department` (str): Department handed to

**Returns:**
- `Feedback`: Created feedback object

**Example:**
```python
from db import add_feedback
from datetime import datetime

feedback = add_feedback(
    fta_id="FTA001",
    feedback_data={
        'email': 'team@example.com',
        'call_type': '1st call',
        'call_success': 'Connected',
        'feedback_1': 'Person very interested in membership',
        'met_date': datetime.now(),
        'department': 'Membership'
    }
)
```

---

#### `get_feedback_by_fta(fta_id: str) -> List[Feedback]`
Retrieves all feedback records for an FTA.

**Parameters:**
- `fta_id` (str): FTA identifier

**Returns:**
- `List[Feedback]`: List of feedback records

**Example:**
```python
from db import get_feedback_by_fta

feedback_list = get_feedback_by_fta("FTA001")
for feedback in feedback_list:
    st.write(f"Call Type: {feedback.call_type}")
    st.write(f"Success: {feedback.call_success}")
```

---

### A-Team Member Functions

#### `add_a_team_member(email: str, full_name: str) -> ATeamMember`
Adds a new A-Team member.

**Parameters:**
- `email` (str): Team member email
- `full_name` (str): Team member full name

**Returns:**
- `ATeamMember`: Created member object

**Example:**
```python
from db import add_a_team_member

member = add_a_team_member(
    email="jane@example.com",
    full_name="Jane Smith"
)
st.success(f"Added {member.full_name}")
```

---

#### `get_all_a_team_members() -> List[ATeamMember]`
Retrieves all active A-Team members.

**Returns:**
- `List[ATeamMember]`: All active team members

**Example:**
```python
from db import get_all_a_team_members

members = get_all_a_team_members()
member_names = [m.full_name for m in members]
st.selectbox("Select Team Member", member_names)
```

---

#### `remove_a_team_member(email: str) -> bool`
Deactivates an A-Team member.

**Parameters:**
- `email` (str): Team member email

**Returns:**
- `True`: If removal successful
- `False`: If member not found

**Example:**
```python
from db import remove_a_team_member

if remove_a_team_member("jane@example.com"):
    st.success("Member removed")
```

---

### Analytics & Reporting Functions

#### `get_user_assignments(user_email: str) -> List[FtaAssignments]`
Retrieves all FTA assignments for a specific user.

**Parameters:**
- `user_email` (str): User's email address

**Returns:**
- `List[FtaAssignments]`: User's assignments

**Example:**
```python
from db import get_user_assignments

assignments = get_user_assignments("john@example.com")
st.write(f"Total assignments: {len(assignments)}")
```

---

#### `get_assignment_count_by_member() -> dict`
Gets count of assignments per team member.

**Returns:**
- `dict`: Mapping of member names to assignment counts

**Example:**
```python
from db import get_assignment_count_by_member

counts = get_assignment_count_by_member()
for member, count in counts.items():
    st.write(f"{member}: {count} assignments")
```

---

#### `get_fta_response_count() -> int`
Gets total count of FTA responses in database.

**Returns:**
- `int`: Total response count

**Example:**
```python
from db import get_fta_response_count

total = get_fta_response_count()
st.metric("Total FTA Responses", total)
```

---

## Database Models Reference

### User Model
```python
from models import User

# Fields
user.id              # int - Primary key
user.name            # str - User full name
user.email           # str - Unique email address
user.password        # str - Hashed password
user.role            # str - "A-Team" or "Admin"

# Relationships
user.assignments     # List[FtaAssignments] - Assigned FTAs
```

---

### FtaAssignments Model
```python
from models import FtaAssignments

# Fields
assignment.id           # int - Primary key
assignment.name         # str - FTA name
assignment.fta_id       # str - Unique FTA identifier
assignment.assigned_to  # str - Team member name
assignment.assigned_by  # int - User ID who assigned
assignment.assigned_at  # datetime - Assignment timestamp

# Relationships
assignment.assigned_by_user  # User - Who assigned it
assignment.responses         # List[FtaResponses]
assignment.submissions       # List[FtaSubmissions]
```

---

### FtaResponses Model
```python
from models import FtaResponses

# Key Fields
response.Full_Name              # str - FTA name
response.Email_address          # str - FTA email
response.Phone_number           # str - FTA phone
response.Gender                 # str - FTA gender
response.Service_Experience     # int - Years of service
response.Worship_Experience     # int - Worship frequency
response.Word_Experience        # float - Scripture knowledge
response.Membership_Interest     # str - Interest in membership
response.Meeting_Date           # datetime - Meeting date
response.FTA_ID                 # str - Foreign key to assignment
```

---

### FtaSubmissions Model
```python
from models import FtaSubmissions

# Fields
submission.full_name           # str - FTA name
submission.phone               # str - Phone number
submission.invited_by          # str - Who invited them
submission.mg_date             # datetime - Meet & Greet date
submission.met_date            # datetime - When they met
submission.location            # str - Meeting location
submission.invited_person_role # str - Role of inviter
submission.comments            # str - Additional comments
submission.submitted_at        # datetime - When submitted
submission.fta_id              # str - FK to assignment
```

---

### Feedback Model
```python
from models import Feedback

# Fields
feedback.email             # str - Team member email
feedback.fta_id            # str - FTA identifier
feedback.call_type         # str - Call type (1st, 2nd call)
feedback.call_success      # str - Success status
feedback.feedback_1        # str - Detailed feedback
feedback.met_date          # datetime - Meeting date
feedback.mg_date           # datetime - M&G date
feedback.department        # str - Department handed to
feedback.general_feedback  # str - Overall notes
feedback.submitted_at      # datetime - Submission time
```

---

## Error Handling

### Common Exceptions

```python
from sqlalchemy.exc import IntegrityError
from db import DatabaseError

# Handle duplicate email
try:
    create_user("John", "john@example.com", "pass", "A-Team")
except IntegrityError:
    st.error("Email already exists")

# Handle missing data
try:
    fta = get_fta_by_id("INVALID")
    if not fta:
        raise ValueError("FTA not found")
except ValueError as e:
    st.error(f"Error: {e}")
```

---

## Examples

### Complete User Registration Flow

```python
from db import create_user, authenticate_user
import streamlit as st

with st.form("registration"):
    name = st.text_input("Full Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["A-Team", "Admin"])
    
    if st.form_submit_button("Register"):
        try:
            user = create_user(name, email, password, role)
            st.success(f"User {user.name} created successfully!")
        except ValueError as e:
            st.error(f"Registration failed: {e}")
```

### FTA Assignment and Tracking

```python
from db import (
    get_user_assignments,
    get_fta_by_id,
    add_feedback
)
from datetime import datetime

# Get user's assignments
assignments = get_user_assignments(st.session_state.email)

# Select FTA to track
fta_id = st.selectbox(
    "Select FTA",
    [a.fta_id for a in assignments]
)

# Get FTA details
fta = get_fta_by_id(fta_id)
st.write(f"Name: {fta.Full_Name}")
st.write(f"Email: {fta.Email_address}")

# Record feedback
with st.form("feedback_form"):
    call_type = st.selectbox("Call Type", ["1st call", "2nd call"])
    call_success = st.radio("Success", ["Connected", "Disconnected", "No answer"])
    feedback_text = st.text_area("Feedback")
    
    if st.form_submit_button("Submit Feedback"):
        add_feedback(fta_id, {
            'email': st.session_state.email,
            'call_type': call_type,
            'call_success': call_success,
            'feedback_1': feedback_text,
            'met_date': datetime.now()
        })
        st.success("Feedback saved!")
```

---

**Last Updated**: April 25, 2026
**Version**: 1.0.0

For more help, see [README.md](README.md) or [DEVELOPMENT.md](DEVELOPMENT.md)

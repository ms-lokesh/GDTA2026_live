# Registration System - Quick Reference

## System Overview

Registration mode has been successfully added to the GDTA 2026 chatbot backend with:
- ✅ Deterministic step-based flow
- ✅ Conditional logic (state only asked for India)
- ✅ Input validation and normalization
- ✅ No database writes (session storage only)
- ✅ Fully integrated with chat interface

## Files Added/Modified

### New Files:
- `logic/registration.py` - Registration logic (275 lines)
- `routes/register.py` - Registration API endpoints
- `test_registration.py` - Comprehensive tests (5/5 passing)

### Modified Files:
- `routes/chat.py` - Added registration_mode handling
- `app.py` - Registered registration blueprint

## Registration Flow

### Step 1: GDTA Affiliation
**Question:** "Is your institution affiliated with GDTA or participating as a GDTA partner?"

**Valid answers:** Yes, No, Not sure (case-insensitive)

### Step 2: Country
**Question:** "Which country are you travelling from?"

**Input:** Free text (any country name)

### Step 3: State (CONDITIONAL)
**Question:** "Which state are you travelling from?"

**Only asked if:** Country == "India" (case-insensitive)

**Otherwise:** State is set to `null` and skipped

### Step 4: Confirmation
**Question:** Review details and confirm

**Actions:**
- CONFIRM → Complete registration
- EDIT → Restart from Step 1

## API Endpoints

### Via Chat Interface (Recommended)

```powershell
# Start registration
$body = '{"message": "I want to register"}'
Invoke-RestMethod -Uri http://localhost:5000/api/chat `
  -Method POST -ContentType "application/json" -Body $body

# Answer questions (continue in chat)
$body = '{"message": "Yes"}'
Invoke-RestMethod -Uri http://localhost:5000/api/chat `
  -Method POST -ContentType "application/json" -Body $body
```

### Direct API (Advanced)

```powershell
# Start registration session
Invoke-RestMethod -Uri http://localhost:5000/api/register/start `
  -Method POST

# Submit answer
$body = '{"answer": "Yes"}'
Invoke-RestMethod -Uri http://localhost:5000/api/register/answer `
  -Method POST -ContentType "application/json" -Body $body

# Check status
Invoke-RestMethod -Uri http://localhost:5000/api/register/status

# Cancel registration
Invoke-RestMethod -Uri http://localhost:5000/api/register/cancel `
  -Method POST
```

## Testing

### Run logic tests:
```bash
python test_registration.py
```

**Expected:** 5/5 tests pass

### Test scenarios covered:
1. ✅ India registration (includes state)
2. ✅ Non-India registration (skips state)
3. ✅ Input validation rules
4. ✅ EDIT flow (restart)
5. ✅ Case insensitive matching

## Example Complete Flow

```
User: "I want to register"
Bot: "Is your institution affiliated with GDTA or participating as a GDTA partner?"
     Options: Yes, No, Not sure

User: "Yes"
Bot: "Thank you. Your GDTA affiliation: Yes"
     "Which country are you travelling from?"

User: "India"
Bot: "Country recorded: India"
     "Which state are you travelling from?"

User: "Maharashtra"
Bot: "State recorded: Maharashtra"
     "Registration Details:
      GDTA Affiliation: Yes
      Country: India
      State: Maharashtra
      
      Type CONFIRM to proceed or EDIT to change your details."

User: "CONFIRM"
Bot: "Registration submitted successfully. Your details have been recorded."
```

## Key Features

### 1. Deterministic Logic
- Same input always produces same result
- No random behavior
- Fully auditable decisions

### 2. Conditional Questions
- State question only for India
- Automatically skipped for other countries
- Case-insensitive country matching

### 3. Input Validation
- GDTA affiliation: Must be Yes/No/Not sure
- Country: Any non-empty text
- State: Any non-empty text
- Confirmation: Must be CONFIRM or EDIT

### 4. Error Handling
- Invalid inputs trigger re-prompts
- Clear error messages
- Can cancel anytime with "cancel" command

### 5. Session Management
- In-memory storage (no database yet)
- Session-based tracking
- Clean-up after completion

## Production Considerations

### Currently NOT Implemented (By Design):
- ❌ Database persistence
- ❌ Email notifications
- ❌ Payment processing
- ❌ Full name/email collection

### To Implement Later:
1. Add database table for registrations
2. Store completed registrations in DB
3. Send confirmation emails
4. Add more fields (name, email, etc.)
5. Integrate with payment system

## Extending the System

### Add new registration field:
1. Add step constant in `RegistrationSteps`
2. Add field to `data` dict
3. Add question in `get_current_question()`
4. Add validation in `validate_input()`
5. Add processing in `process_input()`

### Add conditional logic:
```python
# In process_input() after storing country
if normalized_value.lower() in ['usa', 'canada']:
    # Ask additional question for North America
    registration_state.current_step = RegistrationSteps.REGION
else:
    # Skip to next step
    ...
```

## Restart Instructions

To load the new registration code:

1. Stop the running server (Ctrl+C in python terminal)
2. Restart: `python app.py`
3. Test: Send "I want to register" to `/api/chat`

## Troubleshooting

**Issue:** Registration not working in chat

**Solution:** Server must be restarted after code changes

---

**Issue:** "No active registration session" error

**Solution:** Start registration with "I want to register" first

---

**Issue:** State asked for non-India country

**Solution:** Check case sensitivity - code is case-insensitive for "India"

---

## Status

✅ Registration logic: Complete and tested (5/5 tests passing)
✅ API endpoints: Implemented
✅ Chat integration: Implemented
⏳ Server restart: Required to load new code

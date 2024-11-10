# Matt Limb - Tech Test for MirrorWeb

I use Windows 11 as my primary OS at home. As such, installing `better-sqlite3` into my environment when building the UI, was challenging. It required me to provide the SQLite3 source code. This was not a problem, howver, might be worth noting to future applicants as this was fairly difficult to track down. I totally understand if this is part of the challenge, however, I wanted to ensure the issue was raised if unintended.

## auth.py

### create_session()
- Updated expiry timestamp generation to use timezone-aware timestamps, specifically, UTC timestamps.
  - This is as best-practise in Python Datetime handling.
  - UTC was chosen as it is the base timezone. All other timezones are based off of UTC - so storing all relevant datetimes as UTC allows for conversion into any timezone with minimal complexity, and minimal congnative load for developemnt.
  - This also ensures that all datetimes are consistent across the application. This is especially important for a globally distributed system which share data with each other. Mishandling this can result in users being timed out early, or in extreme cases their newly generated session is no longer valid (mostly appliciable when sessions last a few hours instead of days).
  - Treating all datetimes as UTC (or similar default) would also allow for better rendering on the front-end, as all datetimes can be rendered in the users' local timezone. This aids accessiability and reduces the cognative load on our users. This is relevant to Task 4 on the README.

### get_session() 
- Updated expiry timestamp generation to use timezone-aware timestamps, specifically, UTC timestamps.
  - Reasoning is identical to [create-user](#create_session).

### get_user_from_session() 
- Updated expiry timestamp generation to use timezone-aware timestamps, specifically, UTC timestamps.
  - Reasoning is identical to [create-user](#create_session).

### get_user_by_email() 
- Updated expiry timestamp generation to use timezone-aware timestamps, specifically, UTC timestamps.
  - Reasoning is identical to [create-user](#create_session).


### is_session_expired() 
- Updated expiry timestamp generation to use timezone-aware timestamps, specifically, UTC timestamps.
  - Reasoning is identical to [create-user](#create_session).


## main.py

### Cookies
- Whilst looking through the code, I noticed Cookies are being set. This is concerning to me, becuase the structure of the Remix app used React Server Components, which do not run on the client. 
  - This means FastAPI is setting cookies on our Backend JS layer. JS then passes those onto the browser (I think). This can lead to leaking sessions, and can allow someone to impresonate a session to gain accesss. This is not great.
  - Due to the way sessions are being handled - the cookies on the server are not `httponly`. This is problematic because they can be sent over insecure connections (http, not always https) and they can be accessed/read from JS. This could also allow third-party ads or tracking services or malware to pick up the session cookies and use them to impresonate our users. Not great.
  - To fix this - I would remove the cookie setting measures in FastAPI. The FastAPI routes seem RESTful - so should be able to act without managing the state of the world. As such - I would swap over to using JWTs for authorization, storing them in `secure`, `httponly` and `SameSite` cookies between the browser and Remix backend. The JWT would then be managed by that backend, and sent to FastAPI using the `Authorization` header under the `Bearer` token type. Ideally, authentication of users, and generation of JWTs would be a seperate service (Auth0, Keycloak or similar). FastAPI can then use the validity of the JWT to identify the current user, and verify the correct permissions. 
  - JWTs still run the risk of being stolen - which is why `Secure`, `httponly` and `SameSite` attributes are bieng considered. `httponly` prevents client-side JavaScript from being able to see the cookie. This prevents trackers or malware from being able to access the cookie when on the client. `Secure` prevents http only sites from gaining access, and `SameSite` will prevent non-whitelisted servers from being able to see the cookie. These methods would help to ensure that the JWT is kept as safe as possible, and is only accessiable by the Remix backend.

  - Additionally - this would remove the need for `/login` and `/logout` on the FastAPI backend, as user management will be handled elsewhere, ideally. Of course, the FastAPI backend could be responsible for creating and managing the JWTs and user DB - which has its own security considerations.

### /login
- Updated Endpoint to use PyDantic Model as defined.
  - This allows us to leverage pydantic to check that the required fields for login are present, and the correct type.
  - In the future PyDantic validation can be leveraged to ensure that the values of these fields are structured properly, allowing us to error out early.

- Updated the SQL Query to use the `?` operator for data escaping.
  - This is to ensure our user inputted data is escaped properly. This method helps to prevent a security vulnerability, whereby a bad actor could potentially run arbitary commands on our SQL data, if the data was not properly escaped. Future improvements would be to leverage PyDantic to ensure only valid looking email address strings are passed to the database.

### /messages
- Added Pagination as per Task 1. 
  - This was done by adding the query params (params after the ? in the url), `page_size` and `page`. These were requested in the function body, as opposed to the function signature, to conform to the style of the codebase. This requires an attempt to convert them to an `int` variable, as by default `request.query_params.get()` returns a string value. I catch the resulting error if necessary and feedback to the user. 
  - I set reasonable defaults to the values, 10 for the page_size (as it was the initial value) and 1 for the page number.
  - I then mutated the SQL query to set the LIMIT to the user provided `page_size`, and the offset to the following formula: `(page-1)*page_size`. This formula gets the number of records to skip over.
  - After the query - a check is performed to check over the number of records returned. If a page greater than the first is requested, and no records are returned, then the page is considered invalid, and returns a error to the user.
-  This is a fairly simple form of Pagination. For this context, this pagination scheme is ok, as the number of records is quite small. However, in a system of thousands and millions of records, this pagination technique may be too simple, and can cause bottlenecks on the database, as its reading ALL availiable data, and stepping through each record in the OFFSET one at a time. To fix this, a cursor method of pagination may be more appropriate as we can skip right to the next record needed, reducing the work needed on the database engine. 



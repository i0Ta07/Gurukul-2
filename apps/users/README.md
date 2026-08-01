# Users

## Workings

### Login

Right now the user can register himself and login using the credentials. If an existing user with credentials use o-auth, then his account will automatically be linked with the account with credentials. Then he can use o-auth directly to login.

### Register Email

User enters an email, we will check if it is already taken if not we will save the (email + inc_TTL(bool)) inside Redis with a 5 min TTL. Then we will create a a secret token and sent it to the user email. We are using celery for sending email asynchronously. When user clicks the link, we will check if the value exists in the cache and increase the TTL to 15 minutes and  then `set inc_TTL = True` rendering the rest of the register form. When user sends the POST request we again check if the cache exist and if it does we take the email from redis and attach it to the instance and create the user.

### Change Email

The working is very similar to how django implement forgot password. We will render the profile form that will also contain the email. If the POST request does not contain the email field we will not do anything but if it does we will save the old email for now and save the new email in redis. Now we will use the user_id and convert it to base64 and use `TimestampSigner` to sign and send it to the user's new email. This is because if the user clicks on the link again it will be automatically invalidated since the salt is now the new email. When the user clicks the link we will extract the give user id and try to unsign the string with the extracted user's current email. If the link has been tampered with, we will get a error during unsign. If this all was successful we will get the new email from the redis and update. We have to check for race conditions, if in between user created an account with this email. We then delete the key from the cache and logout him from all devices.

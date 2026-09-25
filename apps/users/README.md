# Users

## Workings

### Login

Right now the user can register himself and login using the credentials. If an existing user with credentials use o-auth, then his account will automatically be linked with the account with credentials. Then he can use o-auth directly to login.

### Register Email

User enters an email, we will check if it is already taken if not we will save the (email + inc_TTL(bool)) inside Redis with a 5 min TTL. Then we will create a a secret token and sent it to the user email. We are using celery for sending email asynchronously. When user clicks the link, we will check if the value exists in the cache and increase the TTL to 15 minutes and  then `set inc_TTL = True` rendering the rest of the register form. When user sends the POST request we again check if the cache exist and if it does we take the email from redis and attach it to the instance and create the user.

### Change Email

The working is very similar to how django implement forgot password. We will render the profile form that will also contain the email. If the POST request does not contain the email field we will not do anything but if it does we will save the old email for now and save the new email in redis. Now we will use the user_id and convert it to base64 and use `TimestampSigner` to sign and send it to the user's new email. This is because if the user clicks on the link again it will be automatically invalidated since the salt is now the new email. When the user clicks the link we will extract the give user id and try to unsign the string with the extracted user's current email. If the link has been tampered with, we will get a error during unsign. If this all was successful we will get the new email from the redis and update. We have to check for race conditions, if in between user created an account with this email. We then delete the key from the cache and logout him from all devices.

### Live Notifications

We could use server side events to trigger notifications but we would have to use `StreamingHttpResponse` to stream real time events as they occur with an ongoing open connection using redis channels. Using SSE, we will open a new connection to a group called `user_notifications_{user.id}`. group_add required two arguments: group_name and channel_name.

Group name is the broadcasting name on which different unique channels can join and receive messages broadcasted on the whole group. It is similar to a whatsapp group in which each channel is a phone number and group is a group. Since this is an open idle connections which waits for service to send messages to `user_notifications_{user.id}` group, we have to stream our responses in real time. Hence we are using `StreamingHttpResponse`.

When an real time event occur such as new Invitation is created, we push a sse payload(event_name + data) into the `user_notifications_{user.id}` group. The event consumer i.e. channel receive them and sends the `StreamingHttpResponse` to the frontend. The event_name is then matched with sse-swap(contains the corresponding event name) of each div that can be updated from these SSE at the frontend.

Streaming response can stream response from database or API directly without any pub/sub (publish/subscribe) queue. Ususally we need those when we are streaming a big file for download from servers. To send real time updates as the notifications we need a pub/sub queue on which we can send the real time updates and the frontend can listen to that queue.

We are not taking the user_id from the kwargs, since we have to authenticate in the view if the request.user.id == given_user_id. So we can just extract the user from the request.

The flow would be:

1. Create a channel connection via a view inside the notification broadcasting group that only contains the user.
2. Wait for 25 seconds to receive a message, if not throw a TimeoutError. When we catch the error and we `yield ": ping"` to write those bytes to the underlying TCP socket of user's browser.

    * If the user is still there: The bytes go through successfully. The browser receives the SSE comment (which it ignores), and the while True loop loops back to waiting for a real message.

    * If the user has already closed the tab, we will have broken pipe error and will not be able to write the bytes. ASGI(Daphne) detects a client disconnect, it calls cancel() on your view's task.  This flags the task as cancelled and throws an asyncio.CancelledError at your current `await yield ": ping"`. We catch it and raise `asyncio.CancelledError` in the except block. Then we reach the finally block in which we will have scheduled a new background task to cleanup redis before the view dies. If we have only used `await` for group_discard, it would not have been exceuted since the task state was cancelled. It would have raised `asyncio.CancelledError` and redis cleanup would have been absorbed.

    Why this is strictly necessary:
    If you never send pings, your code sits indefinitely at the await. The server never tries to write to the socket, so it never discovers the pipe is broken. Furthermore, reverse proxies (like Nginx) or load balancers (like AWS ALB) will silently cuts any HTTP connection that sits perfectly quiet for too long (usually 60 seconds).

    The ping serves two purposes: it keeps the proxy from cutting the connection for being idle, and it forces a "write" operation so the ASGI server can instantly detect if the user actually closed the tab.

    Also, making the cleanup an independent bg task will make sure it always happens.

3. As an event occurs form it's source view, it will send a message to the broadcasting group.
4. This group will broadcast this message to each connection in the group i.e. send it to the single connection from frontend.
5. The frontend will receive the message and make changes according to sse-swap.

## Remeber

* Since we changed the base.html from min-h-screen(scroll if content is more) to h-vdh(no scrolling) we have to manually add the scrollbar for the pages we want to scroll. Do not add overflow-y-auto scrollbar-none to page-container but rather to one class down.

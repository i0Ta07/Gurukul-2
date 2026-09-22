# Chat

## Workings

### Chats

We will use django channels that will upgrade our short lived HTTP connection to a websocket connection (i.e. a single channel). This channel will then be added to a group of channels for broadcasting messages. The group can have as many connections as we want. Like for class groups and 1-1 chats.

### Live Notifications

We could use server side events to trigger notifications but we would have to use `StreamingHttpResponse` to stream real time events as they occur with an ongoing open connection using redis channels. Using SSE, we will open a new connection to a group called `user_notifications_{user.id}`. group_add required two arguments: group_name and channel_name.

Group name is the broadcasting name on which different unique channels can join and receive messages broadcasted on the whole group. It is similar to a whatsapp group in which each channel is a phone number and group is a group. Since this is an open idle connections which waits for service to send messages to `user_notifications_{user.id}` group, we have to stream our responses in real time. Hence we are using `StreamingHttpResponse`.

When an real time event occur such as new Invitation is created, we push a sse payload(event_name + data) into the `user_notifications_{user.id}` group. The frontend consumer i.e. channel receive them and sends the `StreamingHttpResponse` to the frontend. The event_name is then matched with sse-swap(contains the corresponding event name) of each div that can be updated from these SSE at the frontend.

Streaming response can stream response from database or API directly without any pub/sub (publish/subscribe) queue. To send real time updates as the notifications we need a pub/sub queue on which we can send the real time updates and the frontend ca listen to that queue.

The flow would be:

1. Create a channel connection inside the notification broadcasting group from frontend(i.e a View)
2. The connection will wait for messages in the notification group.
3. As an event occurs, it will send a message to the broadcasting group.
4. This group will broadcast this message to each connection in the group.
5. The frontend will receive the message and make changes according to sse-swap.

### Mobile UI for Chats

We have made a seperate but similar UI to the desktop setup. It used the same partials as the Desktop but we have used x-id to dynamically assign the ID to chat-window. When the request is made from either small screen or large screen, the target will be based on the closest `x-id="['chat-window']"` resolved by Alpine and threads or rooms will be replaced there. In mobile, we will have to replace the same chat-window in which threads were shown to load conversations. Therefore inside threads we have `:hx-target="'#' + $id('chat-window')"` which will target the closest chat-window. For desktop, there is a seperate chat-window but for mobile everything happens inside a chat-window.

### Active chat backgroud

This is true beauty, I have never seen it anything like it. the parent container get a `x-data= "{active: null }"`. Now each thread gets `id = {{ thread.id}}  @click="active = {{ thread.id }}" :class="bg=gray-800: active==={{ thread.id }}"`. === checks both the type and value. Now when the user clicks on the thread `active = clicked_thread_id` which makes `active==={{ thread.id }}` = true which in turn makes bg-gray-800 = true and we get our gray background on selected thread. Truely master piece.

### To do list

* Active search HTMX to search for users.
* Load more messages as user scrolls up in the chat.

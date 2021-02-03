import asyncio
import copy
import collections
import functools
import json
from channels.consumer import get_handler_name
from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    MAX_ACTIVE_TASKS = 2

    def __init__(self, *args, **kwargs):
        super(ChatConsumer, self).__init__(*args, **kwargs)
        self.handler_tasks = collections.defaultdict(list)
        self.joined_groups = set()

        self.room_name = None
        self.room_group_name = None

    def complete_task(self, task_instance, handler_name):
        print(f'Complete task for handler {handler_name}, task instance {task_instance}')
        self.handler_tasks[handler_name].remove(task_instance)
        print(
            f'There are still {len(self.handler_tasks[handler_name])} active tasks for'
            f' handler {handler_name}'
        )

    async def dispatch(self, message):
        handler_name = get_handler_name(message)
        handler = getattr(self, handler_name, None)
        if handler:
            if handler_name.startswith('chat_'):
                # Create a task to process message
                loop = asyncio.get_event_loop()
                if len(self.handler_tasks[handler_name]) >= self.MAX_ACTIVE_TASKS:
                    await self.send(text_data=json.dumps({
                        'message': 'MAX_ACTIVE_TASKS reached'
                    }))
                else:
                    handler_task = loop.create_task(handler(message))
                    # don't forget to remove the task from self.handler_tasks
                    # when task completed
                    handler_task.add_done_callback(
                        functools.partial(self.complete_task, handler_name=handler_name)
                    )
                    self.handler_tasks[handler_name].append(handler_task)
            else:
                # The old way to process message
                await handler(message)
        else:
            raise ValueError("No handler for message type %s" % message["type"])

    async def clear_handler_tasks(self):
        for handler_name in self.handler_tasks:
            task_instances = self.handler_tasks[handler_name]
            for task_instance in task_instances:
                task_instance.cancel()
                # try:
                #     await task_instance
                # except asyncio.CancelledError:
                #     print('Cancelled handler task', task_instance)

    async def disconnect(self, code):
        joined_groups = copy.copy(self.joined_groups)
        for group_name in joined_groups:
            await self.leave_group(group_name)
        self.joined_groups.clear()
        await self.clear_handler_tasks()

    async def leave_group(self, group_name):
        await self.channel_layer.group_discard(
            group_name, self.channel_name
        )
        self.joined_groups.remove(group_name)

    async def join_group(self, group_name):
        await self.channel_layer.group_add(
            group_name, self.channel_name
        )
        self.joined_groups.add(group_name)

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        await self.join_group(self.room_group_name)
        await self.accept()

    async def receive(self, text_data=None, bytes_data=None):
        text_json = json.loads(text_data)
        message = text_json['message'].strip()
        if message.endswith('1'):

            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'chat_message',
                'message': message,
            })
        elif message.endswith('2'):
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'chat_message2',
                'message': message,
            })
        else:
            await self.send(text_data=json.dumps({
                'message': 'invalid data'
            }))

    async def chat_message(self, event):
        message = event['message']

        while True:
            print('sending...')
            await self.send(text_data=json.dumps({
                'message': message
            }))
            await asyncio.sleep(1)

    async def chat_message2(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))

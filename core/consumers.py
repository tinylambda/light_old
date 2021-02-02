import json
import asyncio
import logging
import aioredis

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer


class StateConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super(StateConsumer, self).__init__(*args, **kwargs)
        # user's mailbox group,
        self.mailbox_group = None
        self.disconnected = True

    async def connect(self):
        user = self.scope['user']
        if user.is_authenticated:
            self.mailbox_group = f'mailbox_{user.id}'
            await self.channel_layer.group_add(self.mailbox_group, self.channel_name)
            await self.accept()
            self.disconnected = False
        else:
            # refuse connection for not logged in
            await self.close()
            self.disconnected = True

    async def disconnect(self, code):
        logging.error('disconnect called !!!!')
        if self.mailbox_group:
            await self.channel_layer.group_discard(self.mailbox_group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        text_json = json.loads(text_data)
        message = text_json['message']
        print(message, '!!!!')
        message = message.strip()
        if message.strip() == 'init':
            await self.channel_layer.group_send(self.mailbox_group, {
                'type': 'message_init',
            })
        elif message == 'chat':
            await self.channel_layer.group_send(self.mailbox_group, {
                'type': 'message_chat',
                'message': message,
            })
        else:
            print('DUMMY')

    async def message_chat(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))

    async def message_init(self, event):
        await asyncio.sleep(1)
        await self.send(text_data=json.dumps({
            'message': 'init state of user'
        }))
        while not self.disconnected:
            await asyncio.sleep(1)
            await self.send(text_data=json.dumps({
                'message': 'most updated state refresh!'
            }))
            print('one round...')


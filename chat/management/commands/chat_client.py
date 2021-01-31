import os
import sys
import json
import signal
import typing
import asyncio
import websockets

from django.core.management.base import BaseCommand, CommandError


def get_stdin_data(q):
    """data from stdin"""
    asyncio.ensure_future(q.put(sys.stdin.readline()))


async def simple_ws(
        uri: typing.AnyStr,
        on_open: typing.Callable = None,
        on_message: typing.Callable = None,
        on_error: typing.Callable = None,
        q: asyncio.Queue = None,
):
    """a simple WebSocket client"""
    def call_function(f, *args):
        if f:
            f(*args)

    loop = asyncio.get_event_loop()
    async with websockets.connect(uri, extra_headers=[]) as client_side_ws:
        call_function(on_open)
        i = 0
        while True:
            try:
                user_input_task = loop.create_task(q.get())
                ws_recv_task = loop.create_task(client_side_ws.recv())
                tasks = [user_input_task, ws_recv_task]

                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                if user_input_task.done():
                    user_input = user_input_task.result()
                    data = json.dumps({'message': user_input})
                    await client_side_ws.send(data)

                msg = None
                if ws_recv_task.done():
                    msg = ws_recv_task.result()
                    call_function(on_message, msg)

                # Cancel remaining tasks so they do not generate errors as we exit without finishing them.
                for task in tasks:
                    if not task.done():
                        task.cancel()

                if msg is not None:
                    msg_dict: typing.Dict = json.loads(msg)
                    message: typing.AnyStr = msg_dict.get('message')
                    if message and message.strip() == 'bye':
                        break
            except Exception as e:
                call_function(on_error, e)


class Command(BaseCommand):
    help = 'Start a chat client'

    def add_arguments(self, parser):
        parser.add_argument('ws_url', nargs='?', help='WebSocket url',
                            type=str, default='ws://127.0.0.1:8000/ws/chat/cc/')

    def handle(self, *args, **options):
        ws_url = options['ws_url']

        loop = asyncio.get_event_loop()
        q = asyncio.Queue()
        loop.add_reader(sys.stdin, get_stdin_data, q)

        loop.run_until_complete(
            simple_ws(
                uri=ws_url,
                on_open=lambda: print('connected'),
                on_message=lambda msg: print('Received: ', msg),
                on_error=lambda e: print('Error: ', e),
                q=q,
            )
        )

        self.stdout.write(self.style.SUCCESS("Done"))



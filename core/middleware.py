class CoreMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Before
        response = self.get_response(request)
        # After
        return response


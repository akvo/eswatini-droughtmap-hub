from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination


class Pagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "current": self.page.number,
                "total": self.page.paginator.count,
                "total_page": self.page.paginator.num_pages,
                "data": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        return {
            "type": "object",
            "properties": {
                "current": {
                    "type": "integer",
                    "example": 123,
                },
                "total": {
                    "type": "integer",
                    "example": 123,
                },
                "total_page": {
                    "type": "integer",
                    "example": 123,
                },
                "data": schema,
            },
        }


class ClampedPagination(Pagination):
    """Serve the last page instead of 404 when the page runs off the end.

    For a SHRINKING worklist, "page 6 of 5" is a stale bookmark rather than a
    bad request. The review queue's "Awaiting review" filter drops a row on
    every submission, so a reviewer returned to the page they came from — or
    reloading one — lands past the end as soon as the list gets short enough,
    and DRF's default answer is a 404 ("Invalid page.") that takes the whole
    page render down with it.

    `num_pages` is never below 1, so an emptied queue clamps to page 1 and
    returns no rows rather than raising.
    """

    def get_page_number(self, request, paginator):
        number = super().get_page_number(request, paginator)
        # super() resolves the "last page" aliases to an int already; anything
        # non-numeric left over is invalid input and still deserves its 404.
        if str(number).isdigit():
            return min(int(number), paginator.num_pages)
        return number

"""Legacy Django reporting views, mounted at /reports via WSGI."""

from django.db import connection
from django.http import HttpResponse
from django.utils.html import escape

from .models import Order


def revenue(request):
    region = request.GET.get("region", "EU")
    qs = Order.objects.filter(region=region)
    return HttpResponse("Total orders: %d" % qs.count())


def daily(request):
    day = request.GET.get("day", "")
    with connection.cursor() as c:
        c.execute("SELECT SUM(total) FROM orders WHERE day = %s", [day])
        total = c.fetchone()[0]
    return HttpResponse(f"<p>Report for {escape(day)}: {total}</p>")


def by_status(request):
    status = request.GET.get("status", "paid")
    if status not in {"paid", "pending", "refunded"}:
        return HttpResponse("unknown status", status=400)
    qs = Order.objects.raw("SELECT * FROM orders WHERE status = %s", [status])
    return HttpResponse("<p>%d rows</p>" % len(list(qs)))

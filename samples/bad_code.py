"""Deliberately AI-unfriendly code, used to demo airead."""

CONFIG = {"api_key": "secret"}
COUNTER = 0


def process(d, x):
    global COUNTER
    COUNTER += 1
    if x:
        return d["a"] + d["b"]
    return d["a"]


def do_stuff(data):
    import json
    import os
    result = []
    for i in range(len(data)):
        if data[i] > 0:
            if data[i] < 100:
                if data[i] % 2 == 0:
                    result.append(data[i] * 2)
                else:
                    result.append(data[i] * 3)
            else:
                result.append(0)
        else:
            result.append(-1)
    print(json.dumps(result))
    open(os.path.join("/tmp", "out.json"), "w").write(json.dumps(result))
    return result


def get_user(uid):
    user = {"id": uid, "name": "x"}
    user["last_seen"] = "now"
    user.update({"touched": True})
    CONFIG["last_uid"] = uid
    return user


def is_valid(u):
    u["validated"] = True
    return u["id"] > 0


def handle(req):
    a = req.get("a")
    b = req.get("b")
    c = req.get("c")
    if a:
        if b:
            if c:
                return a + b + c
            return a + b
        return a
    return None


def calculate_total(items):
    """Pure function done well — should score high."""
    return sum(item.price * item.quantity for item in items)


def fetch_active_users(database):
    """Honest getter — also good."""
    return [u for u in database.users if u.is_active]


class OrderService:
    def save_order(self, order):
        self.orders.append(order)
        return order.id

    def get_total(self, order):
        order.viewed = True
        return sum(i.price for i in order.items)

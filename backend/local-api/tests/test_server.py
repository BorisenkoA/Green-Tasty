import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class LocalApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.previous_admin_email = os.environ.get("LOCAL_API_ADMIN_EMAIL")
        os.environ["LOCAL_API_ADMIN_EMAIL"] = "admin@example.test"
        cls.data_dir = Path(cls.temp_dir.name)
        server.DATA_DIR = cls.data_dir
        server.DATABASE_PATH = cls.data_dir / "test.sqlite3"
        server.SECRET_PATH = cls.data_dir / "secret"
        server.initialize_database()
        handler = type("TestApiHandler", (server.ApiHandler,), {})
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.httpd.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)
        cls.temp_dir.cleanup()
        if cls.previous_admin_email is None:
            os.environ.pop("LOCAL_API_ADMIN_EMAIL", None)
        else:
            os.environ["LOCAL_API_ADMIN_EMAIL"] = cls.previous_admin_email

    def request(self, method, path, body=None, token=None):
        payload = None if body is None else json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(
            self.base_url + path, data=payload, headers=headers, method=method
        )
        try:
            with urlopen(request) as response:
                response_body = response.read()
                if not response_body:
                    value = None
                elif response.headers.get_content_type() == "application/json":
                    value = json.loads(response_body)
                else:
                    value = response_body
                return response.status, value
        except HTTPError as error:
            response_body = error.read()
            status = error.code
            error.close()
            return status, json.loads(response_body) if response_body else None

    def test_seeded_locations_and_popular_dishes_are_available(self):
        locations_status, locations = self.request("GET", "/locations")
        dishes_status, dishes = self.request("GET", "/dishes/popular")
        self.assertEqual(locations_status, 200)
        self.assertEqual(dishes_status, 200)
        self.assertEqual(len(locations), 3)
        self.assertEqual(len(dishes), 4)
        self.assertTrue(all(location["imageUrl"].startswith("assets/") for location in locations))
        self.assertTrue(all(dish["state"] == "Available" for dish in dishes))
        assets_dir = (
            Path(__file__).resolve().parents[3]
            / "frontend/restaurant-frontend-app/src/assets"
        )
        self.assertTrue(
            all(
                (assets_dir / item["imageUrl"].removeprefix("assets/")).is_file()
                for item in locations + dishes
            )
        )

    def test_registration_password_sign_in_and_authorized_profile(self):
        registration = {
            "firstName": "Taylor",
            "lastName": "Green",
            "email": "taylor.green@example.com",
            "password": "Secure@123",
            "confirmPassword": "Secure@123",
        }
        status, response = self.request("POST", "/register", registration)
        self.assertEqual(status, 201, response)
        duplicate_status, duplicate = self.request("POST", "/register", registration)
        self.assertEqual(duplicate_status, 409)
        self.assertIn("already exists", duplicate["error"])
        wrong_password_status, _ = self.request(
            "POST", "/signin", {"email": registration["email"], "password": "wrongpass"}
        )
        self.assertEqual(wrong_password_status, 401)

        sign_in_status, tokens = self.request(
            "POST",
            "/signin",
            {"email": registration["email"], "password": registration["password"]},
        )
        self.assertEqual(sign_in_status, 200)
        self.assertEqual(tokens["idToken"], tokens["accessToken"])
        profile_status, profile = self.request("GET", "/me", token=tokens["idToken"])
        self.assertEqual(profile_status, 200)
        self.assertEqual(profile["email"], registration["email"])
        self.assertEqual(profile["role"], "Customer")

    def test_profile_requires_a_valid_token(self):
        status, body = self.request("GET", "/me")
        self.assertEqual(status, 401)
        self.assertIn("error", body)

    def register_and_sign_in(self, email="booking@example.com"):
        if email.startswith("admin"):
            os.environ["LOCAL_API_ADMIN_EMAIL"] = email
        password = "Secure@123"
        registration = {
            "firstName": "Taylor",
            "lastName": "Green",
            "email": email,
            "password": password,
            "confirmPassword": password,
        }
        status, response = self.request("POST", "/register", registration)
        self.assertEqual(status, 201, response)
        status, tokens = self.request(
            "POST", "/signin", {"email": email, "password": password}
        )
        self.assertEqual(status, 200)
        return tokens["idToken"]

    def test_booking_and_preorder_lifecycle(self):
        token = self.register_and_sign_in()
        status, tables = self.request(
            "GET",
            "/available-tables?locationId=9%20Abashidze%20Street%2C%20Tbilisi&capacity=2",
            token=token,
        )
        self.assertEqual(status, 200)
        self.assertTrue(tables)
        table_id = tables[0]["id"]
        reservation_body = {
            "tableId": table_id,
            "startTime": "2030-07-01T11:00:00Z",
            "endTime": "2030-07-01T12:30:00Z",
            "guestCount": 2,
        }
        status, reservation = self.request(
            "POST", "/reservations", reservation_body, token=token
        )
        self.assertEqual(status, 201, reservation)
        reservation_id = reservation["id"]
        self.assertEqual(reservation["locationAddress"], "9 Abashidze Street, Tbilisi")

        conflict_status, _ = self.request(
            "POST", "/reservations", reservation_body, token=token
        )
        self.assertEqual(conflict_status, 409)
        listed_status, reservations = self.request("GET", "/reservations", token=token)
        self.assertEqual(listed_status, 200)
        self.assertEqual(len(reservations), 1)

        dishes_status, dishes = self.request("GET", "/dishes/popular")
        self.assertEqual(dishes_status, 200)
        status, order = self.request(
            "POST",
            "/orders",
            {
                "reservationId": reservation_id,
                "orderItems": [{"dishId": dishes[0]["id"], "quantity": 2}],
            },
            token=token,
        )
        self.assertEqual(status, 201, order)
        self.assertEqual(order["orderItems"][0]["dish"]["id"], dishes[0]["id"])
        status, _ = self.request(
            "PUT",
            f"/orders/{reservation_id}",
            {"orderItems": [{"dishId": dishes[0]["id"], "quantity": 3}]},
            token=token,
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            self.request("GET", f"/orders/{reservation_id}", token=token)[1]["orderItems"][0]["quantity"],
            3,
        )
        self.assertEqual(
            self.request("POST", f"/orders/{reservation_id}/submit", {}, token=token)[0],
            204,
        )
        self.assertEqual(
            self.request("POST", f"/orders/{reservation_id}/unsubmit", {}, token=token)[0],
            204,
        )
        other_customer = self.register_and_sign_in("other-customer@example.com")
        self.assertEqual(
            self.request("GET", f"/reservations/{reservation_id}", token=other_customer)[0],
            403,
        )
        self.assertEqual(
            self.request("GET", f"/orders/{reservation_id}", token=other_customer)[0],
            403,
        )
        self.assertEqual(
            self.request(
                "GET",
                f"/reservations/{reservation_id}/invite-token",
                token=other_customer,
            )[0],
            403,
        )

    def test_guest_invite_and_feedback_flows(self):
        token = self.register_and_sign_in("guest-flow@example.com")
        _, table = self.request(
            "GET",
            "/available-tables?locationId=location-baratashvili&capacity=3",
            token=token,
        )
        _, reservation = self.request(
            "POST",
            "/reservations",
            {
                "tableId": table[0]["id"],
                "startTime": "2030-08-02T13:00:00Z",
                "endTime": "2030-08-02T14:30:00Z",
                "guestCount": 3,
            },
            token=token,
        )
        reservation_id = reservation["id"]
        status, invite_token = self.request(
            "GET", f"/reservations/{reservation_id}/invite-token", token=token
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            self.request("GET", f"/guest/invites/{invite_token['token']}")[1][
                "GroupReservationId"
            ],
            reservation_id,
        )
        status, created_session = self.request(
            "POST",
            "/guest/sessions",
            {"groupReservationId": reservation_id, "guestName": "Guest One"},
        )
        self.assertEqual(status, 201, created_session)
        session_id = created_session["SessionId"]
        session_token = created_session["SessionToken"]
        _, menu = self.request(
            "GET",
            f"/guest/sessions/{session_id}/menu",
            token=session_token,
        )
        dish = next(iter(menu["dishes"].values()))[0]
        self.assertEqual(
            self.request(
                "POST",
                f"/guest/sessions/{session_id}/dishes",
                {"dishId": dish["id"], "quantity": 2},
                token=session_token,
            )[0],
            204,
        )
        self.assertEqual(
            self.request(
                "DELETE",
                f"/guest/sessions/{session_id}/dishes",
                {"dishId": dish["id"], "quantity": 1},
                token=session_token,
            )[0],
            204,
        )
        self.assertEqual(
            self.request(
                "POST", f"/guest/sessions/{session_id}/submit", {}, token=session_token
            )[0],
            204,
        )
        self.assertEqual(self.request("GET", f"/guest/groups/{reservation_id}/sessions")[0], 200)
        self.assertEqual(self.request("GET", f"/guest/groups/{reservation_id}/status")[0], 200)
        self.assertEqual(
            self.request("GET", f"/reservations/{reservation_id}/feedback"),
            (200, None),
        )
        status, feedback = self.request(
            "POST",
            "/feedback",
            {
                "reservationId": reservation_id,
                "rating": 5,
                "comment": "Great",
                "type": 0,
            },
            token=token,
        )
        self.assertEqual(status, 201, feedback)
        self.assertEqual(feedback["locationId"], "location-baratashvili")
        self.assertEqual(
            self.request(
                "GET",
                f"/feedback?locationId=location-baratashvili&type=0&sort=NewestFirst&page=1",
                token=token,
            )[1]["items"][0]["rating"],
            5,
        )

    def test_admin_can_manage_menu_and_local_reporting(self):
        token = self.register_and_sign_in("admin@example.test")
        status, dish = self.request(
            "POST",
            "/dishes",
            {
                "name": "Local special",
                "description": "Test dish",
                "dishType": "MainCourse",
                "price": 12,
                "weight": "200 g",
                "calories": "100 kcal",
                "proteins": "5 g",
                "fats": "4 g",
                "carbohydrates": "10 g",
                "vitamins": "C",
                "state": "Available",
                "locationIds": ["location-abashidze"],
            },
            token=token,
        )
        self.assertEqual(status, 201, dish)
        self.assertEqual(
            self.request("GET", f"/locations/location-abashidze/dishes")[0], 200
        )
        self.assertTrue(
            any(
                row["id"] == dish["id"]
                for row in self.request(
                    "GET", "/locations/location-abashidze/dishes"
                )[1]
            )
        )
        self.assertEqual(
            self.request(
                "GET",
                "/reports/generate?type=0&startDate=2030-01-01&endDate=2030-12-31&locationId=location-abashidze",
                token=token,
            )[0],
            200,
        )
        self.assertEqual(self.request("GET", "/reports", token=token)[0], 200)
        pdf_status, pdf = self.request(
            "GET",
            "/reports/download?type=1&startDate=2030-01-01&endDate=2030-12-31&locationId=location-abashidze&format=pdf",
            token=token,
        )
        self.assertEqual(pdf_status, 200)
        self.assertTrue(pdf.startswith(b"%PDF-1.4"))
        self.assertEqual(
            self.request("DELETE", f"/dishes/{dish['id']}", token=token)[0], 204
        )

    def test_waiter_notifications_table_and_reservation_management(self):
        admin_token = self.register_and_sign_in("admin-waiter@example.test")
        self.register_and_sign_in("waiter@example.com")
        self.assertEqual(
            self.request(
                "POST",
                "/waiters",
                {"email": "waiter@example.com"},
                token=admin_token,
            )[0],
            200,
        )
        waiter_status, waiter_tokens = self.request(
            "POST",
            "/signin",
            {"email": "waiter@example.com", "password": "Secure@123"},
        )
        self.assertEqual(waiter_status, 200)
        waiter_token = waiter_tokens["idToken"]
        waiter_status, waiter = self.request("GET", "/me", token=waiter_token)
        self.assertEqual(waiter_status, 200)
        self.assertEqual(waiter["role"], "Waiter")
        self.assertEqual(
            self.request(
                "GET", f"/waiters/{waiter['id']}/location", token=waiter_token
            )[1]["locationId"],
            "location-abashidze",
        )

        table_status, new_table = self.request(
            "POST",
            "/tables",
            {"locationId": "location-abashidze", "tableNumber": 99, "capacity": 4},
            token=admin_token,
        )
        self.assertEqual(table_status, 201)
        self.assertEqual(
            self.request(
                "PUT",
                f"/tables/{new_table['id']}",
                {"capacity": 5},
                token=admin_token,
            )[0],
            200,
        )
        self.assertEqual(
            self.request(
                "GET", "/locations/location-abashidze/tables/all", token=waiter_token
            )[0],
            200,
        )
        self.assertEqual(
            self.request(
                "GET",
                f"/tables/{new_table['id']}/available-time-slots?startTime=2030-09-10T00:00:00Z",
                token=waiter_token,
            )[0],
            200,
        )

        customer_token = self.register_and_sign_in("customer@example.com")
        reservation_status, reservation = self.request(
            "POST",
            "/reservations",
            {
                "tableId": new_table["id"],
                "startTime": "2030-09-10T12:00:00Z",
                "endTime": "2030-09-10T13:30:00Z",
                "guestCount": 3,
            },
            token=customer_token,
        )
        self.assertEqual(reservation_status, 201)
        self.assertEqual(reservation["waiterId"], waiter["id"])
        notification_status, notifications = self.request(
            "GET", "/notifications", token=waiter_token
        )
        self.assertEqual(notification_status, 200)
        self.assertEqual(notifications[0]["reservationId"], reservation["id"])
        notification_id = notifications[0]["id"]
        self.assertEqual(
            self.request(
                "PATCH", f"/notifications/{notification_id}/read", {}, token=waiter_token
            )[0],
            204,
        )
        self.assertTrue(
            self.request("GET", "/notifications", token=waiter_token)[1][0]["isRead"]
        )
        self.assertEqual(
            self.request(
                "PATCH",
                f"/reservations/{reservation['id']}/status",
                {"newStatus": 2},
                token=waiter_token,
            )[0],
            200,
        )
        self.assertEqual(
            self.request(
                "PUT",
                "/reservations",
                {
                    "reservationId": reservation["id"],
                    "startTime": "2030-09-10T12:30:00Z",
                    "endTime": "2030-09-10T14:00:00Z",
                    "guestCount": 2,
                },
                token=customer_token,
            )[0],
            200,
        )
        self.assertEqual(
            self.request(
                "DELETE",
                "/reservations",
                {"id": reservation["id"]},
                token=customer_token,
            )[0],
            200,
        )
        self.assertEqual(
            self.request(
                "DELETE", f"/tables/{new_table['id']}", token=admin_token
            )[0],
            204,
        )

    def test_customer_profile_and_local_location_management(self):
        token = self.register_and_sign_in("profile@example.com")
        _, user = self.request("GET", "/me", token=token)
        self.assertEqual(
            self.request(
                "PUT",
                "/me",
                {"firstName": "Taylor", "lastName": "Updated"},
                token=token,
            )[0],
            204,
        )
        self.assertEqual(
            self.request("GET", f"/users/{user['id']}/name", token=token)[1]["name"],
            "Taylor Updated",
        )
        self.assertEqual(
            self.request(
                "PUT",
                "/me/profile-image",
                {"base64Image": "iVBORw0KGgo="},
                token=token,
            )[0],
            200,
        )
        self.assertTrue(
            self.request(
                "GET", f"/users/{user['id']}/profile-image", token=token
            )[1]["presignedUrl"].startswith("data:image/jpeg;base64,")
        )
        self.assertEqual(
            self.request(
                "PUT",
                "/me/change-password",
                {"oldPassword": "Secure@123", "newPassword": "NewSecure@123"},
                token=token,
            )[0],
            204,
        )
        self.assertEqual(
            self.request(
                "POST",
                "/signin",
                {"email": "profile@example.com", "password": "NewSecure@123"},
            )[0],
            200,
        )

        admin_token = self.register_and_sign_in("admin-profile@example.test")
        status, location = self.request(
            "POST",
            "/locations",
            {
                "address": "1 Local Street, Tbilisi",
                "description": "A test restaurant",
                "totalCapacity": 12,
                "averageOccupancy": "50%",
                "rating": 4.5,
            },
            token=admin_token,
        )
        self.assertEqual(status, 201)
        self.assertEqual(
            self.request(
                "PUT",
                f"/locations/{location['id']}",
                {"description": "Updated restaurant"},
                token=admin_token,
            )[0],
            200,
        )
        self.assertEqual(
            self.request("DELETE", f"/locations/{location['id']}", token=admin_token)[0],
            204,
        )


if __name__ == "__main__":
    unittest.main()

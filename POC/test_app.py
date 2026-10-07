import os
import time
import io
import unittest
import app

class FlowDroidAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.app.test_client()
        cls.test_apk_path = os.path.join(
            app.BASE_DIR, "flowdroid_poc", "DroidBench", "apk", "AndroidSpecific", "DirectLeak1.apk"
        )

    def test_01_index_page(self):
        """Verify main HTML page loads properly with AndroidGuard & DSS elements."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("AndroidGuard", html)
        self.assertIn("Android Privacy Compliance", html)
        self.assertIn("Google Play Data Safety", html)
        self.assertIn("Select Android APK", html)
        self.assertIn("Live Execution Console", html)

    def test_02_successful_run(self):
        """Verify running FlowDroid on DirectLeak1.apk produces SUCCESS with findings."""
        if not os.path.exists(self.test_apk_path) or not os.path.exists(app.FLOWDROID_JAR):
            self.skipTest("FlowDroid JAR or test APK not found locally.")

        with open(self.test_apk_path, "rb") as f:
            apk_bytes = f.read()

        data = {
            "apk_file": (io.BytesIO(apk_bytes), "DirectLeak1.apk"),
            "timeout": "60"
        }
        resp = self.client.post("/api/run", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        res_json = resp.get_json()
        self.assertTrue(res_json.get("success"))
        run_id = res_json["run_id"]

        # Poll until finished
        max_wait = 40
        start = time.time()
        final_data = None
        while time.time() - start < max_wait:
            poll_resp = self.client.get(f"/api/poll/{run_id}?since_line=0")
            self.assertEqual(poll_resp.status_code, 200)
            poll_data = poll_resp.get_json()
            if poll_data.get("status") == "completed":
                final_data = poll_data
                break
            time.sleep(1.0)

        self.assertIsNotNone(final_data, "Analysis did not complete within max_wait")
        self.assertEqual(final_data["outcome"], "SUCCESS")
        self.assertGreaterEqual(final_data["findings_count"], 1)
        self.assertTrue(final_data["xml_available"])
        self.assertIsNotNone(final_data["results"])

        # Check raw XML download endpoint
        dl_resp = self.client.get(f"/api/download/{run_id}/xml")
        self.assertEqual(dl_resp.status_code, 200)
        content = dl_resp.get_data(as_text=True)
        dl_resp.close()
        self.assertIn("DataFlowResults", content)

        # Check history
        hist_resp = self.client.get("/api/history")
        self.assertEqual(hist_resp.status_code, 200)
        history = hist_resp.get_json()
        self.assertTrue(any(h["run_id"] == run_id for h in history))

        # Check run details endpoint
        detail_resp = self.client.get(f"/api/run/{run_id}")
        self.assertEqual(detail_resp.status_code, 200)
        details = detail_resp.get_json()
        self.assertEqual(details["outcome"], "SUCCESS")

    def test_03_timeout_enforcement(self):
        """Verify strict timeout termination results in TIMEOUT outcome and kills process."""
        if not os.path.exists(self.test_apk_path) or not os.path.exists(app.FLOWDROID_JAR):
            self.skipTest("FlowDroid JAR or test APK not found locally.")

        with open(self.test_apk_path, "rb") as f:
            apk_bytes = f.read()

        data = {
            "apk_file": (io.BytesIO(apk_bytes), "DirectLeak1.apk"),
            "timeout": "1"  # 1 second timeout will reliably trigger on FlowDroid startup
        }
        resp = self.client.post("/api/run", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        run_id = resp.get_json()["run_id"]

        max_wait = 15
        start = time.time()
        final_data = None
        while time.time() - start < max_wait:
            poll_resp = self.client.get(f"/api/poll/{run_id}")
            poll_data = poll_resp.get_json()
            if poll_data.get("status") == "completed":
                final_data = poll_data
                break
            time.sleep(0.5)

        self.assertIsNotNone(final_data, "Timeout run did not complete in time")
        self.assertEqual(final_data["outcome"], "TIMEOUT")

    def test_04_invalid_file_extension(self):
        """Verify rejection of non-apk files."""
        data = {
            "apk_file": (io.BytesIO(b"not an apk"), "document.pdf"),
            "timeout": "60"
        }
        resp = self.client.post("/api/run", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Only .apk files are supported", resp.get_json()["error"])

    def test_05_corrupt_apk_crash_outcome(self):
        """Verify that passing an invalid/corrupt APK results in a CRASH outcome with crash snippet."""
        data = {
            "apk_file": (io.BytesIO(b"corrupted apk data header"), "corrupt.apk"),
            "timeout": "60"
        }
        resp = self.client.post("/api/run", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        run_id = resp.get_json()["run_id"]

        max_wait = 20
        start = time.time()
        final_data = None
        while time.time() - start < max_wait:
            poll_resp = self.client.get(f"/api/poll/{run_id}")
            poll_data = poll_resp.get_json()
            if poll_data.get("status") == "completed":
                final_data = poll_data
                break
            time.sleep(0.5)

        self.assertIsNotNone(final_data)
        self.assertEqual(final_data["outcome"], "CRASH")
        self.assertIsNotNone(final_data.get("crash_snippet"))
        self.assertGreater(len(final_data["crash_snippet"]), 0)

    def test_06_clear_history(self):
        """Verify clearing history clears the in-memory store and file."""
        clear_resp = self.client.post("/api/history/clear")
        self.assertEqual(clear_resp.status_code, 200)
        self.assertTrue(clear_resp.get_json()["success"])

        hist_resp = self.client.get("/api/history")
        self.assertEqual(hist_resp.status_code, 200)
        self.assertEqual(hist_resp.get_json(), [])

    def test_07_zero_leak_run(self):
        """Verify that zero-leak APK produces SUCCESS with 0 findings in results and history."""
        noleak_apk_path = os.path.join(
            app.BASE_DIR, "flowdroid_poc", "DroidBench", "apk", "AndroidSpecific", "LogNoLeak.apk"
        )
        if not os.path.exists(noleak_apk_path) or not os.path.exists(app.FLOWDROID_JAR):
            self.skipTest("FlowDroid JAR or test APK not found locally.")

        with open(noleak_apk_path, "rb") as f:
            apk_bytes = f.read()

        data = {
            "apk_file": (io.BytesIO(apk_bytes), "LogNoLeak.apk"),
            "timeout": "60"
        }
        resp = self.client.post("/api/run", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        run_id = resp.get_json()["run_id"]

        max_wait = 30
        start = time.time()
        final_data = None
        while time.time() - start < max_wait:
            poll_resp = self.client.get(f"/api/poll/{run_id}")
            poll_data = poll_resp.get_json()
            if poll_data.get("status") == "completed":
                final_data = poll_data
                break
            time.sleep(0.5)

        self.assertIsNotNone(final_data)
        self.assertEqual(final_data["outcome"], "SUCCESS")
        self.assertEqual(final_data["findings_count"], 0)
        self.assertIsNone(final_data.get("crash_snippet"))
        self.assertIsNotNone(final_data.get("results"))
        self.assertEqual(final_data["results"]["total_findings"], 0)

        # Check that history table has outcome SUCCESS and findings_count 0
        hist_resp = self.client.get("/api/history")
        self.assertEqual(hist_resp.status_code, 200)
        history = hist_resp.get_json()
        target_entry = next((h for h in history if h["run_id"] == run_id), None)
        self.assertIsNotNone(target_entry)
        self.assertEqual(target_entry["outcome"], "SUCCESS")
        self.assertEqual(target_entry["findings_count"], 0)

    def test_08_extract_dss_benchmark_apk(self):
        """Verify extracting DSS on a benchmark APK (DirectLeak1.apk) extracts package name and handles unlisted status."""
        if not os.path.exists(self.test_apk_path):
            self.skipTest("Benchmark APK not found.")

        with open(self.test_apk_path, "rb") as f:
            apk_bytes = f.read()

        data = {
            "apk_file": (io.BytesIO(apk_bytes), "DirectLeak1.apk")
        }
        resp = self.client.post("/api/extract-dss", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        res_json = resp.get_json()
        self.assertEqual(res_json.get("package_name"), "de.ecspride")
        self.assertIn("error", res_json)
        self.assertIn("not found on Google Play", res_json["error"])

    def test_09_extract_dss_real_playstore_apk(self):
        """Verify extracting DSS on a real Google Play APK extracts full metadata and declarations."""
        real_apk_path = os.path.join(
            app.BASE_DIR, "flowdroid_poc", "apks", "large", "Quran, 16 Lines, Colored.apk"
        )
        if not os.path.exists(real_apk_path):
            self.skipTest(f"Real APK not found at {real_apk_path}")

        with open(real_apk_path, "rb") as f:
            apk_bytes = f.read()

        data = {
            "apk_file": (io.BytesIO(apk_bytes), "Quran, 16 Lines, Colored.apk")
        }
        resp = self.client.post("/api/extract-dss", data=data, content_type="multipart/form-data")
        self.assertEqual(resp.status_code, 200)
        res_json = resp.get_json()
        self.assertEqual(res_json.get("package_name"), "com.paranthesis.quranpaktajweedi")
        self.assertNotIn("error", res_json)
        self.assertIn("app_name", res_json)
        self.assertIn("developer", res_json)
        self.assertIn("icon_url", res_json)
        self.assertIn("is_data_encrypted", res_json)
        self.assertIn("is_data_deletion_supported", res_json)
        self.assertIsInstance(res_json.get("data_collected"), list)
        self.assertIsInstance(res_json.get("data_shared"), list)

    def test_10_extract_dss_by_run_id(self):
        """Verify extracting DSS via run_id parameter."""
        if not os.path.exists(self.test_apk_path):
            self.skipTest("Benchmark APK not found.")

        with open(self.test_apk_path, "rb") as f:
            apk_bytes = f.read()

        data = {
            "apk_file": (io.BytesIO(apk_bytes), "DirectLeak1.apk"),
            "timeout": "1"  # Quick timeout just to register run_id
        }
        run_resp = self.client.post("/api/run", data=data, content_type="multipart/form-data")
        self.assertEqual(run_resp.status_code, 200)
        run_id = run_resp.get_json()["run_id"]

        # Call extract-dss by run_id
        dss_resp = self.client.post("/api/extract-dss", data={"run_id": run_id})
        self.assertEqual(dss_resp.status_code, 200)
        res_json = dss_resp.get_json()
        self.assertEqual(res_json.get("package_name"), "de.ecspride")

if __name__ == "__main__":
    unittest.main()


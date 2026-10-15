"""Képküldési helyreállítás valódi, hálózattól elzárt Chromium motorral."""
from __future__ import annotations

import json
import unittest

import test_modern_webengine as modern
import test_webengine as baseline


class ImageRecoveryWebEngineTests(unittest.TestCase):
    setUpClass = classmethod(baseline.WebEngineStagingTests.setUpClass.__func__)
    setUp = baseline.WebEngineStagingTests.setUp
    tearDown = baseline.WebEngineStagingTests.tearDown
    raw_javascript = baseline.WebEngineStagingTests.raw_javascript
    deliver = baseline.WebEngineStagingTests.deliver
    load_fixture = modern.ModernWebEngineTests.load_fixture

    def prepare(self, source):
        self.load_fixture(source)
        # Kizárólag az offline példány óráit rövidítjük; az alkalmazás
        # teljes feltöltési és visszaigazolási határideje változatlan.
        replacements = {
            "const IMAGE_SUBMISSION_CONFIRMATION_TIMEOUT_MS = 8000;":
                "const IMAGE_SUBMISSION_CONFIRMATION_TIMEOUT_MS = 250;",
            "const SUBMISSION_RETRY_GUARD_MS = 2200;":
                "const SUBMISSION_RETRY_GUARD_MS = 60;",
            "return Math.min(60000, Math.max(20, Number(payload.pageReadyTimeoutMs) || 25000));":
                "return 250;",
        }
        for old, new in replacements.items():
            self.assertIn(old, self.harness.automation_script)
            self.harness.automation_script = self.harness.automation_script.replace(old, new)

    def image_delivery(self):
        result = self.deliver(
            imageDataUrl=modern.IMAGE, imageFilename="mentett-kivagas.png",
            imageMimeType="image/png", waitForResponse=True,
            copyResponseToClipboard=False, responseTimeoutMs=5000,
        )
        self.assertEqual(result["assistantResponseText"], "Azonos kész fordítás.")
        self.assertTrue(result["assistantResponseComplete"])
        self.assertEqual(self.page.errors, [])
        self.assertEqual(self.blocker.blocked, [])
        return result

    def tracking_fixture(self):
        return modern.live_heading_image_fixture(history=False).replace(
            "attachment.addEventListener('change',()=>{",
            """document.body.dataset.attachmentAttempts='0';
const savedImages=[];
attachment.addEventListener('change',()=>{
  document.body.dataset.attachmentAttempts=String(Number(document.body.dataset.attachmentAttempts)+1);
  const reader=new FileReader(); reader.onload=()=>{
    savedImages.push(reader.result); document.body.dataset.savedImages=JSON.stringify(savedImages);
  }; reader.readAsDataURL(attachment.files[0]);""",
        )

    def assert_saved_image_reused(self, attempts):
        images = json.loads(self.raw_javascript("document.body.dataset.savedImages"))
        self.assertEqual(images, [modern.IMAGE] * attempts)
        self.assertEqual(self.raw_javascript("document.body.dataset.attachmentAttempts"), str(attempts))

    def test_unacknowledged_upload_restarts_with_original_image(self):
        source = self.tracking_fixture().replace(
            "const preview=document.createElement('img');",
            "if(Number(document.body.dataset.attachmentAttempts)===1) return;\n"
            "  const preview=document.createElement('img');",
        )
        self.prepare(source)
        self.image_delivery()
        self.assert_saved_image_reused(2)
        self.assertEqual(self.raw_javascript("document.body.dataset.submitCount"), "1")

    def test_disappearing_draft_without_chat_message_restarts_from_original_image(self):
        source = self.tracking_fixture().replace(
            "event.preventDefault(); count++;",
            """event.preventDefault();
  if(Number(document.body.dataset.attachmentAttempts)===1){
    composer.replaceChildren(); attachment.value='';
    for(const preview of document.querySelectorAll('form img')) preview.remove();
    return;
  }
  count++;""",
        )
        self.prepare(source)
        self.image_delivery()
        self.assert_saved_image_reused(2)
        self.assertEqual(self.raw_javascript("document.body.dataset.submitCount"), "1")

    def test_visible_image_waits_for_slow_answer_without_restart(self):
        self.prepare(self.tracking_fixture())
        self.image_delivery()
        self.assert_saved_image_reused(1)
        self.assertEqual(self.raw_javascript("document.body.dataset.submitCount"), "1")
        self.assertEqual(self.raw_javascript("document.body.dataset.finished"), "true")

    def test_stuck_preview_is_removed_before_same_image_is_attached_again(self):
        source = self.tracking_fixture().replace(
            "document.querySelector('form').append(preview);",
            """const holder=document.createElement('div');
  const remove=document.createElement('button'); remove.type='button';
  remove.setAttribute('aria-label','Remove image'); remove.textContent='Remove image';
  remove.addEventListener('click',()=>{
    holder.remove(); attachment.value='';
    document.body.dataset.removedCount=String(Number(document.body.dataset.removedCount||0)+1);
  });
  holder.append(preview,remove); document.querySelector('form').append(holder);""",
        ).replace(
            "event.preventDefault(); count++;",
            "event.preventDefault(); if(Number(document.body.dataset.attachmentAttempts)===1) return; count++;",
        )
        self.prepare(source)
        self.image_delivery()
        self.assert_saved_image_reused(2)
        self.assertEqual(self.raw_javascript("document.body.dataset.removedCount"), "1")
        self.assertEqual(self.raw_javascript("document.body.dataset.submitCount"), "1")

    def test_persistent_upload_failure_stops_after_three_attempts(self):
        source = self.tracking_fixture().replace(
            "const preview=document.createElement('img');",
            "return;\n  const preview=document.createElement('img');",
        )
        self.prepare(source)
        with self.assertRaisesRegex(RuntimeError, "kép|Kép"):
            self.deliver(imageDataUrl=modern.IMAGE, imageFilename="mentett-kivagas.png",
                         imageMimeType="image/png", waitForResponse=True)
        self.assert_saved_image_reused(3)
        self.assertEqual(self.raw_javascript("document.body.dataset.submitCount"), "0")
        self.assertEqual(self.page.errors, [])
        self.assertEqual(self.blocker.blocked, [])

    def test_late_chat_message_inside_confirmation_window_does_not_duplicate(self):
        source = self.tracking_fixture().replace(
            "document.querySelector('main').append(turn);",
            "setTimeout(()=>document.querySelector('main').append(turn),120);",
        )
        self.prepare(source)
        self.image_delivery()
        self.assert_saved_image_reused(1)
        self.assertEqual(self.raw_javascript("document.body.dataset.submitCount"), "1")


if __name__ == "__main__":
    unittest.main()

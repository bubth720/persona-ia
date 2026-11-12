package ia.persona.app

import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import ia.persona.app.data.Library
import ia.persona.app.engine.EngineClient
import ia.persona.app.ui.GenerateActivity
import ia.persona.app.ui.MainActivity
import ia.persona.app.ui.ReferencesActivity
import ia.persona.app.ui.ResultsActivity
import ia.persona.app.ui.SettingsActivity
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.File

/**
 * T10/T11 sur émulateur. Le moteur utilisé en CI est le backend de TEST non génératif
 * (aucun GPU en CI) : ce test prouve le parcours import → job → revue → export,
 * PAS la génération photoréaliste.
 */
@RunWith(AndroidJUnit4::class)
class EndToEndTest {
    private val inst = InstrumentationRegistry.getInstrumentation()
    private val ctx = inst.targetContext

    private fun synthPng(seed: Int): ByteArray {
        val b = Bitmap.createBitmap(256, 256, Bitmap.Config.ARGB_8888)
        val c = Canvas(b)
        c.drawColor(Color.rgb(seed * 37 % 255, seed * 91 % 255, seed * 53 % 255))
        c.drawCircle(128f, 110f, 60f + seed % 20, Paint().apply { color = Color.WHITE })
        return ByteArrayOutputStream().also { b.compress(Bitmap.CompressFormat.PNG, 100, it) }.toByteArray()
    }

    @Test fun screensOpenWithoutCrash() {
        for (cls in listOf(MainActivity::class.java, ReferencesActivity::class.java, GenerateActivity::class.java,
                ResultsActivity::class.java, SettingsActivity::class.java)) {
            val a = inst.startActivitySync(Intent(ctx, cls).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            inst.waitForIdleSync()
            a.finish()
        }
    }

    @Test fun libraryImport300OnDevice() {
        val lib = Library(File(ctx.cacheDir, "lib-${System.nanoTime()}"))
        var n = 0
        for (i in 0 until 300) if (lib.importStream("s$i.png", ByteArrayInputStream(synthPng(i % 290)), true).outcome == Library.Outcome.IMPORTED) n++
        assertEquals(290, n)
        assertEquals(290, Library(lib.root).all().size)
    }

    @Test fun fullJourneyAgainstWorker() {
        val args = InstrumentationRegistry.getArguments()
        val url = args.getString("engineUrl") ?: return        // pas de moteur fourni : test ignoré
        val token = args.getString("engineToken") ?: return
        val e = EngineClient(url, token)
        assertTrue(e.health().getBoolean("ok"))
        val lib = Library(File(ctx.cacheDir, "lib-e2e-${System.nanoTime()}"))
        repeat(3) { lib.importStream("ref$it.png", ByteArrayInputStream(synthPng(it + 7)), true) }
        val refs = lib.selectForEngine("face")
        val job = e.createJob("face", 7L, JSONObject().put("subject_class", "person"), "ci")
        val id = job.getString("id")
        refs.forEach { e.uploadAuthorizedReference(id, it.sha256, lib.fileFor(it).readBytes()) }
        e.start(id)
        var st = e.getStatus(id)
        val t0 = System.currentTimeMillis()
        while (st.getString("state") !in setOf("succeeded", "failed") && System.currentTimeMillis() - t0 < 120_000) {
            Thread.sleep(500); st = e.getStatus(id)
        }
        assertEquals("succeeded", st.getString("state"))
        assertEquals(6, st.getJSONObject("views").length())
        val png = e.fetchOutput(id, "face")
        assertTrue(png[1] == 'P'.code.toByte())
        e.review(id, "face", false, "test rejet")
        e.regenerate(id, "face")
        Thread.sleep(500)
        while (e.getStatus(id).getString("state") !in setOf("succeeded", "failed")) Thread.sleep(500)
        e.review(id, "profil_gauche", true, "test accept")
        val m = e.rebuildBoard(id)
        assertEquals("layout_test_only", m.getString("status"))   // backend de test : jamais une réussite Gate D
        assertTrue(e.fetchBoard(id).size > 1000)
        e.deleteJob(id)
    }
}

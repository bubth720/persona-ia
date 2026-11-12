package ia.persona.app

import ia.persona.app.data.Library
import ia.persona.app.engine.EngineClient
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.File
import java.nio.file.Files
import kotlin.random.Random

class LibraryTest {
    private fun fakePng(seed: Int): ByteArray {
        val r = Random(seed)
        return byteArrayOf(0x89.toByte(), 'P'.code.toByte(), 'N'.code.toByte(), 'G'.code.toByte()) + ByteArray(200) { r.nextInt().toByte() }
    }

    @Test fun import1000NoLossDuplicatesReported() {
        val root = Files.createTempDirectory("lib").toFile()
        val lib = Library(root)
        var imported = 0; var dup = 0
        for (i in 0 until 1000) {
            val bytes = fakePng(if (i % 50 == 49) i - 1 else i)       // 20 exact duplicates
            when (lib.importStream("p$i.png", ByteArrayInputStream(bytes), true).outcome) {
                Library.Outcome.IMPORTED -> imported++
                Library.Outcome.DUPLICATE -> dup++
                Library.Outcome.ERROR -> fail("erreur inattendue")
            }
        }
        assertEquals(980, imported); assertEquals(20, dup)
        assertEquals(980, Library(root).all().size)                  // survit à la réouverture
        root.deleteRecursively()
    }

    @Test fun interruptedImportRecoversAndKeepsAnnotations() {
        val root = Files.createTempDirectory("lib").toFile()
        val lib = Library(root)
        val first = lib.importStream("a.png", ByteArrayInputStream(fakePng(1)), true).sha256!!
        lib.annotate(first, view = "face", validated = true)
        // orphelin copié mais non journalisé + fichier temporaire + ligne de journal tronquée
        val bytes = fakePng(2)
        val sha = Library.sha256(ByteArrayInputStream(bytes))
        File(root, "originals/${sha.substring(0, 2)}").apply { mkdirs() }.resolve("$sha.png").writeBytes(bytes)
        File(root, "originals/.tmp-123.png").writeBytes(byteArrayOf(1, 2))
        File(root, "journal.jsonl").appendText("{\"op\":\"imp")
        val again = Library(root)
        assertEquals(listOf(sha), again.recovered)
        assertFalse(again.get(sha)!!.authorized)
        assertEquals("face", again.get(first)!!.view)
        assertEquals(1, again.coverage()["face"])
        assertFalse(File(root, "originals/.tmp-123.png").exists())
        root.deleteRecursively()
    }

    @Test fun consentAndFormatRefusals() {
        val lib = Library(Files.createTempDirectory("lib").toFile())
        try { lib.importStream("a.png", ByteArrayInputStream(fakePng(3)), false); fail() } catch (_: Library.ConsentException) { }
        assertEquals(Library.Outcome.ERROR, lib.importStream("a.gif", ByteArrayInputStream(fakePng(3)), true).outcome)
        assertEquals(Library.Outcome.ERROR, lib.importStream("a.png", ByteArrayInputStream(ByteArray(50)), true).outcome)
        assertTrue(lib.all().isEmpty())
        assertTrue(lib.missingViews().contains("dos"))
    }

    @Test fun engineUrlPolicy() {
        EngineClient.validateUrl("http://10.0.2.2:8765")
        EngineClient.validateUrl("http://192.168.1.20:8765")
        EngineClient.validateUrl("https://engine.example.org")
        for (bad in listOf("http://example.org", "http://8.8.8.8:80", "ftp://10.0.0.1")) {
            try { EngineClient.validateUrl(bad); fail(bad) } catch (_: Exception) { }
        }
    }
}

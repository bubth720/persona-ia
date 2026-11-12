package ia.persona.app.ui

import android.app.Activity
import android.content.Intent
import android.graphics.BitmapFactory
import android.graphics.Color
import android.os.Bundle
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.ArrayAdapter
import android.widget.AdapterView
import android.view.View
import ia.persona.app.engine.EngineClient
import org.json.JSONObject
import java.io.File
import java.util.concurrent.Executors
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/** Résultats : comparer aux références, accepter/rejeter, régénérer une vue, exporter planche + manifeste. */
class ResultsActivity : Activity() {
    private val io = Executors.newSingleThreadExecutor()
    private lateinit var body: LinearLayout
    private var jobId: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val col = screen("Résultats")
        val jobs = App.jobs(this)
        if (jobs.isEmpty()) { col.label("Aucune génération pour l'instant."); return }
        val chooser = Spinner(this).apply {
            adapter = ArrayAdapter(this@ResultsActivity, android.R.layout.simple_spinner_dropdown_item, jobs.map { "Job ${it.take(8)}" })
        }
        col.addView(chooser)
        col.button("Actualiser") { load() }
        col.button("Exporter planche + vues + manifeste (ZIP)") { exportZip() }
        body = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        col.addView(body)
        chooser.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: AdapterView<*>?, v: View?, pos: Int, id: Long) { jobId = jobs[pos]; load() }
            override fun onNothingSelected(p: AdapterView<*>?) {}
        }
    }

    private fun load() {
        val id = jobId ?: return
        val e = App.engine(this)
        val dir = App.resultsDir(this, id)
        io.execute {
            val remote: JSONObject? = try {
                e?.getStatus(id)?.also { File(dir, "status.json").writeText(it.toString(2)) }
            } catch (_: Exception) { null }
            val status: JSONObject? = remote
                ?: File(dir, "status.json").takeIf { it.exists() }?.let { JSONObject(it.readText()) }
            if (status == null) { ui { body.removeAllViews(); body.label("Moteur injoignable et aucun résultat local.", color = Color.RED) }; return@execute }
            val views = status.getJSONObject("views")
            // Télécharger les sorties terminées (cache local => consultation hors ligne)
            if (e != null) for (v in views.keys()) {
                val st = views.getJSONObject(v).getString("state")
                val f = File(dir, "$v.png")
                if (st in setOf("done", "accepted", "rejected")) try {
                    val sha = views.getJSONObject(v).optJSONObject("provenance")?.optString("sha256")
                    if (!f.exists() || sha == null || ia.persona.app.data.Library.sha256(f.inputStream()) != sha)
                        f.writeBytes(e.fetchOutput(id, v))
                } catch (_: Exception) { }
            }
            if (e != null) try {
                File(dir, "manifest.json").writeText(e.fetchManifest(id).toString(2))
                File(dir, "planche.png").writeBytes(e.fetchBoard(id))
            } catch (_: Exception) { }
            ui { render(id, status, dir, e) }
        }
    }

    private fun render(id: String, status: JSONObject, dir: File, e: EngineClient?) {
        body.removeAllViews()
        val generative = status.optJSONObject("backend")?.optBoolean("is_generation", false) ?: false
        body.label("État : ${status.getString("state")} · ${status.getString("kind")}", bold = true)
        if (!generative) body.label("MOTEUR DE TEST NON GÉNÉRATIF : ces images ne sont pas des générations et ne valident aucune planche.",
            14f, color = Color.RED)
        File(dir, "planche.png").takeIf { it.exists() }?.let { f ->
            body.label("Planche", bold = true)
            body.addView(ImageView(this).apply { adjustViewBounds = true; setImageBitmap(BitmapFactory.decodeFile(f.path)) })
        }
        val views = status.getJSONObject("views")
        for (v in views.keys()) {
            val s = views.getJSONObject(v)
            body.label("${VIEW_LABELS[v] ?: v} — ${s.getString("state")} (essai ${s.optInt("attempts")})", bold = true)
            s.optJSONObject("provenance")?.let { p ->
                body.label("seed ${p.optLong("seed")} · ${p.optString("engine")} · ${p.optDouble("duration_s")} s" +
                    (p.optJSONArray("warnings")?.let { w -> (0 until w.length()).joinToString("") { "\n⚠ " + w.getString(it) } } ?: ""), 12f)
            }
            val f = File(dir, "$v.png")
            if (f.exists()) body.addView(ImageView(this).apply {
                adjustViewBounds = true
                setImageBitmap(BitmapFactory.decodeFile(f.path, BitmapFactory.Options().apply { inSampleSize = 2 }))
            }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
            if (e != null && s.getString("state") in setOf("done", "accepted", "rejected")) {
                val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
                fun act(label: String, block: () -> Unit) = row.addView(Button(this).apply {
                    text = label; isAllCaps = false
                    setOnClickListener { io.execute { try { block(); ui { load() } } catch (x: Exception) { ui { body.label("Erreur : ${x.message}", color = Color.RED) } } } }
                }, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
                act("Accepter") { e.review(id, v, true, "validée visuellement sur Android"); e.rebuildBoard(id) }
                act("Rejeter") { e.review(id, v, false, "rejetée sur Android"); e.rebuildBoard(id) }
                act("Régénérer") { e.regenerate(id, v) }
                body.addView(row)
            }
        }
        body.label("Validation humaine : comparer yeux, nez, bouche, implantation des cheveux, asymétries, mains et pieds " +
            "avec les références. Les régions non photographiées sont des estimations.", 12f)
    }

    private fun exportZip() {
        val id = jobId ?: return
        startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE); type = "application/zip"
            putExtra(Intent.EXTRA_TITLE, "persona_${id.take(8)}.zip")
        }, REQ_EXPORT)
    }

    @Deprecated("Activity API")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        val uri = data?.data
        if (requestCode != REQ_EXPORT || resultCode != RESULT_OK || uri == null) return
        val dir = App.resultsDir(this, jobId ?: return)
        io.execute {
            try {
                val tmp = File(cacheDir, "export.zip")
                ZipOutputStream(tmp.outputStream()).use { z ->
                    dir.listFiles()?.sortedBy { it.name }?.forEach { f ->
                        z.putNextEntry(ZipEntry(f.name)); f.inputStream().use { it.copyTo(z) }; z.closeEntry()
                    }
                }
                contentResolver.openOutputStream(uri)!!.use { out -> tmp.inputStream().use { it.copyTo(out) } }
                tmp.delete()
                ui { body.label("Export terminé.", color = Color.rgb(0, 110, 0)) }
            } catch (x: Exception) { ui { body.label("Export interrompu : ${x.message}. Relancez l'export.", color = Color.RED) } }
        }
    }

    override fun onDestroy() { io.shutdown(); super.onDestroy() }

    companion object { const val REQ_EXPORT = 42 }
}

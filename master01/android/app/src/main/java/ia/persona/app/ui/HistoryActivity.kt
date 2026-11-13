package ia.persona.app.ui

import android.app.Activity
import android.app.AlertDialog
import android.content.ContentValues
import android.content.Intent
import android.graphics.BitmapFactory
import android.graphics.Color
import android.os.Bundle
import android.provider.MediaStore
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.LinearLayout
import ia.persona.app.engine.LocalJobs
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** Historique hors ligne : image, paramètres, modèle, seed ; export, partage, suppression, avis visuel. */
class HistoryActivity : Activity() {
    private lateinit var body: LinearLayout
    private var exportId: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val col = screen("Historique")
        body = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        col.addView(body)
        render(intent.getStringExtra("open"))
    }

    private fun render(open: String?) {
        body.removeAllViews()
        val items = LocalJobs.history(this)
        if (items.isEmpty()) { body.label("Aucune génération pour l'instant."); return }
        val fmt = SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.FRANCE)
        for (m in items) {
            val id = m.getString("id")
            val dir = File(LocalJobs.historyDir(this), id)
            val ok = m.optString("status") == "generated"
            body.label("${fmt.format(Date(m.optLong("created_ms")))} — " + (if (ok) "génération réussie techniquement" else "échec : ${m.optString("error")}"),
                bold = true, color = if (ok) Color.BLACK else Color.RED)
            val img = File(dir, "result.png")
            if (ok && img.isFile) body.addView(ImageView(this).apply {
                adjustViewBounds = true
                setImageBitmap(BitmapFactory.decodeFile(img.path, BitmapFactory.Options().apply { inSampleSize = if (id == open) 1 else 2 }))
            }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
            body.label("« ${m.optString("user_description")} » · ${m.optInt("width")}×${m.optInt("height")} · ${m.optInt("steps")} pas · " +
                "seed ${m.optLong("seed")} · ${m.optString("profile")} · ${"%.0f".format(m.optDouble("seconds", 0.0))} s · " +
                "RAM pic ${m.optLong("peak_rss_mb")} Mo · ${m.optJSONArray("references")?.length() ?: 0} réf.", 12f)
            body.label("Ressemblance (votre avis) : " + when (m.optString("likeness")) {
                "yes" -> "satisfaisante"; "no" -> "insuffisante"; else -> "non évaluée" }, 12f)
            val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
            fun act(t: String, f: () -> Unit) = row.addView(Button(this).apply { text = t; isAllCaps = false; setOnClickListener { f() } },
                LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            if (ok) {
                act("Ressemble") { rate(dir, m, "yes") }
                act("Ne ressemble pas") { rate(dir, m, "no") }
                act("Exporter") { exportId = id; startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE); type = "image/png"; putExtra(Intent.EXTRA_TITLE, "persona_$id.png") }, REQ_EXPORT) }
                act("Partager") { share(img) }
            }
            act("Supprimer") {
                AlertDialog.Builder(this).setMessage("Supprimer cette génération ?")
                    .setPositiveButton("Supprimer") { _, _ -> LocalJobs.deleteEntry(this, id); render(null) }
                    .setNegativeButton("Annuler", null).show()
            }
            body.addView(row)
        }
        body.label("Les fichiers exportés ne contiennent pas les photos de référence. « Réussite technique » ≠ ressemblance : jugez visuellement.", 12f)
    }

    private fun rate(dir: File, m: JSONObject, v: String) {
        m.put("likeness", v); File(dir, "meta.json").writeText(m.toString(2)); render(m.getString("id"))
    }

    private fun share(img: File) {
        // Copie volontaire dans Images/PERSONA puis partage Android (aucune métadonnée de référence).
        val values = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, "persona_${System.currentTimeMillis()}.png")
            put(MediaStore.Images.Media.MIME_TYPE, "image/png")
            put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/PERSONA")
        }
        val uri = contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values) ?: return
        contentResolver.openOutputStream(uri)!!.use { out -> img.inputStream().use { it.copyTo(out) } }
        startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
            type = "image/png"; putExtra(Intent.EXTRA_STREAM, uri); addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION) }, "Partager"))
    }

    @Deprecated("Activity API")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        val uri = data?.data ?: return
        val id = exportId ?: return
        if (requestCode != REQ_EXPORT || resultCode != RESULT_OK) return
        val img = File(File(LocalJobs.historyDir(this), id), "result.png")
        contentResolver.openOutputStream(uri)!!.use { out -> img.inputStream().use { it.copyTo(out) } }
        body.label("Exporté.", color = Color.rgb(0, 110, 0))
    }

    companion object { const val REQ_EXPORT = 61 }
}

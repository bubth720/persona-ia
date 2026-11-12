package ia.persona.app.ui

import android.app.Activity
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.util.LruCache
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.BaseAdapter
import android.widget.CheckBox
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.ListView
import android.widget.Spinner
import android.widget.TextView
import ia.persona.app.data.Library
import java.util.concurrent.Executors

/** Références : importer (lots, reprise), visualiser, corriger le classement, voir les vues manquantes. */
class ReferencesActivity : Activity() {
    private val io = Executors.newSingleThreadExecutor()
    private lateinit var lib: Library
    private lateinit var progress: TextView
    private lateinit var coverage: TextView
    private lateinit var consent: CheckBox
    private lateinit var adapter: RefAdapter
    private val thumbs = LruCache<String, Bitmap>(200)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        title = "Références"
        lib = App.library(this)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(12), dp(12), dp(12), 0) }
        consent = CheckBox(this).apply {
            text = "Je déclare que l'usage de ces photographies et de la ressemblance de la personne adulte représentée est autorisé."
            isChecked = App.prefs(this@ReferencesActivity).getBoolean("import_consent", false)
            setOnCheckedChangeListener { _, c -> App.prefs(this@ReferencesActivity).edit().putBoolean("import_consent", c).apply() }
        }
        root.addView(consent)
        root.button("Importer des photos (JPG, PNG, WEBP)") { pick() }
        progress = root.label("", 14f)
        coverage = root.label("", 14f)
        adapter = RefAdapter()
        val list = ListView(this).apply { adapter = this@ReferencesActivity.adapter }
        root.addView(list, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        setContentView(root)
        if (lib.recovered.isNotEmpty())
            progress.text = "${lib.recovered.size} fichier(s) récupéré(s) après interruption : autorisation à reconfirmer."
        refresh()
        if (savedInstanceState == null && intent.getBooleanExtra("import", false)) pick()
    }

    private fun pick() {
        if (!consent.isChecked) {
            progress.setTextColor(Color.RED)
            progress.text = "Import refusé : cochez d'abord la déclaration d'autorisation."
            return
        }
        val i = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "image/*"
            putExtra(Intent.EXTRA_MIME_TYPES, arrayOf("image/jpeg", "image/png", "image/webp"))
            putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
        }
        startActivityForResult(i, REQ_PICK)
    }

    @Deprecated("Activity API")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQ_PICK || resultCode != RESULT_OK || data == null) return
        val uris = mutableListOf<Uri>()
        data.clipData?.let { c -> for (k in 0 until c.itemCount) uris.add(c.getItemAt(k).uri) }
        data.data?.let { if (uris.isEmpty()) uris.add(it) }
        importAll(uris)
    }

    private fun displayName(uri: Uri): String =
        contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
            if (c.moveToFirst()) c.getString(0) else null
        } ?: (uri.lastPathSegment ?: "image")

    private fun importAll(uris: List<Uri>) {
        progress.setTextColor(Color.DKGRAY)
        io.execute {
            var imported = 0; var dup = 0; var err = 0
            uris.forEachIndexed { idx, uri ->
                val r = try {
                    contentResolver.openInputStream(uri)!!.use { lib.importStream(displayName(uri), it, consent.isChecked) }
                } catch (e: Exception) {
                    Library.ImportResult(Library.Outcome.ERROR, null, e.message ?: "erreur")
                }
                when (r.outcome) {
                    Library.Outcome.IMPORTED -> imported++
                    Library.Outcome.DUPLICATE -> dup++
                    Library.Outcome.ERROR -> err++
                }
                if (idx % 10 == 0 || idx == uris.size - 1) ui {
                    progress.text = "Import ${idx + 1}/${uris.size} · nouvelles $imported · doublons signalés $dup · erreurs $err"
                    refresh()
                }
            }
        }
    }

    private fun refresh() {
        val cov = lib.coverage()
        val missing = lib.missingViews()
        coverage.text = "Couverture (classements validés) : " +
            cov.filter { it.value > 0 }.entries.joinToString { "${VIEW_LABELS[it.key]} ${it.value}" }.ifEmpty { "aucune" } +
            "\nVues manquantes : " + missing.joinToString { VIEW_LABELS[it] ?: it }.ifEmpty { "aucune" } +
            "\nLes vues absentes ne sont jamais inventées : elles seront marquées « estimé »."
        coverage.setTextColor(if (missing.isEmpty()) Color.rgb(0, 110, 0) else Color.rgb(160, 60, 0))
        adapter.items = lib.all()
        adapter.notifyDataSetChanged()
    }

    private fun thumb(ref: Library.Ref): Bitmap? {
        thumbs.get(ref.sha256)?.let { return it }
        val f = lib.fileFor(ref)
        val o = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(f.path, o)
        var s = 1
        while (o.outWidth / (s * 2) >= 96 && o.outHeight / (s * 2) >= 96) s *= 2
        val b = BitmapFactory.decodeFile(f.path, BitmapFactory.Options().apply { inSampleSize = s }) ?: return null
        thumbs.put(ref.sha256, b)
        return b
    }

    inner class RefAdapter : BaseAdapter() {
        var items: List<Library.Ref> = emptyList()
        override fun getCount() = items.size
        override fun getItem(p: Int) = items[p]
        override fun getItemId(p: Int) = p.toLong()
        override fun getView(position: Int, convertView: View?, parent: ViewGroup?): View {
            val ref = items[position]
            val row = LinearLayout(this@ReferencesActivity).apply {
                orientation = LinearLayout.HORIZONTAL
                setPadding(0, dp(4), 0, dp(4))
            }
            val img = ImageView(this@ReferencesActivity).apply { scaleType = ImageView.ScaleType.CENTER_CROP }
            row.addView(img, LinearLayout.LayoutParams(dp(72), dp(72)))
            io.execute { val b = thumb(ref); ui { img.setImageBitmap(b) } }
            val col = LinearLayout(this@ReferencesActivity).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(8), 0, 0, 0) }
            col.addView(TextView(this@ReferencesActivity).apply {
                text = "${ref.sourceName}\n${ref.sha256.take(12)}… · ${ref.size / 1024} Ko" + if (!ref.authorized) " · AUTORISATION À RECONFIRMER" else ""
                textSize = 12f
            })
            val spinner = Spinner(this@ReferencesActivity)
            val views = Library.REFERENCE_VIEWS
            spinner.adapter = ArrayAdapter(this@ReferencesActivity, android.R.layout.simple_spinner_dropdown_item,
                views.map { VIEW_LABELS[it] ?: it })
            spinner.setSelection(views.indexOf(ref.view))
            spinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(p: AdapterView<*>?, v: View?, pos: Int, id: Long) {
                    if (views[pos] != ref.view) { lib.annotate(ref.sha256, view = views[pos]); refresh() }
                }
                override fun onNothingSelected(p: AdapterView<*>?) {}
            }
            col.addView(spinner)
            val validated = CheckBox(this@ReferencesActivity).apply {
                text = "classement vérifié"
                isChecked = ref.validated
                setOnCheckedChangeListener { _, c -> lib.annotate(ref.sha256, validated = c); refresh() }
            }
            col.addView(validated)
            if (!ref.authorized) col.addView(android.widget.Button(this@ReferencesActivity).apply {
                text = "Reconfirmer l'autorisation"; isAllCaps = false
                setOnClickListener { lib.confirmConsent(ref.sha256); refresh() }
            })
            row.addView(col, LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f))
            return row
        }
    }

    override fun onDestroy() { io.shutdown(); super.onDestroy() }

    companion object { const val REQ_PICK = 41 }
}

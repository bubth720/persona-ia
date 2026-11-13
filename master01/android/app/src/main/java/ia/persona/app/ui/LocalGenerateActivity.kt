package ia.persona.app.ui

import android.app.Activity
import android.app.ActivityManager
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.graphics.BitmapFactory
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import ia.persona.app.data.Library
import ia.persona.app.engine.GenerationService
import ia.persona.app.engine.LocalJobs
import org.json.JSONArray
import org.json.JSONObject
import kotlin.random.Random

/** Génération 100 % locale sur le téléphone : références, description, format, profil, graine. */
class LocalGenerateActivity : Activity() {
    private lateinit var refsView: LinearLayout
    private lateinit var refsLabel: TextView
    private lateinit var stage: TextView
    private lateinit var generate: Button
    private lateinit var cancel: Button
    private lateinit var checks: TextView
    private var selected = mutableListOf<String>()
    private val listener: (LocalJobs.Status) -> Unit = { s -> ui { render(s) } }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val col = screen("Générer sur le téléphone")
        col.label("Génération locale (sans réseau)", 20f, bold = true, color = Color.BLACK)
        checks = col.label("", 13f)
        refsLabel = col.label("", 14f, bold = true)
        refsView = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        col.addView(refsView)
        col.button("Choisir les références (1 à 4 visages nets)") { chooseRefs() }
        col.label("Sujet", 13f)
        val subjects = listOf("woman", "man")
        val subject = Spinner(this).apply {
            adapter = ArrayAdapter(this@LocalGenerateActivity, android.R.layout.simple_spinner_dropdown_item, listOf("femme", "homme"))
        }
        col.addView(subject)
        val desc = EditText(this).apply {
            hint = "Description (anglais conseillé) : ex. smiling, in a park, autumn light, wearing a red coat"
            setText(App.prefs(this@LocalGenerateActivity).getString("local_desc", "head and shoulders portrait, looking at the camera"))
        }
        col.addView(desc)
        col.label("Format", 13f)
        val formats = listOf("portrait", "carre", "paysage")
        val format = Spinner(this).apply {
            adapter = ArrayAdapter(this@LocalGenerateActivity, android.R.layout.simple_spinner_dropdown_item, listOf("Portrait", "Carré", "Paysage"))
        }
        col.addView(format)
        col.label("Profil (les deux sont réellement appliqués)", 13f)
        val profiles = LocalJobs.profiles()
        val profile = Spinner(this).apply {
            adapter = ArrayAdapter(this@LocalGenerateActivity, android.R.layout.simple_spinner_dropdown_item, profiles.map { it.label })
            setSelection(1)
        }
        col.addView(profile)
        val seed = EditText(this).apply { hint = "Graine (vide = aléatoire)"; inputType = InputType.TYPE_CLASS_NUMBER }
        col.addView(seed)
        col.label("Fidélité au visage (force PhotoMaker : plus bas = plus proche des références)", 13f)
        val strengths = listOf(10, 20, 35)
        val strength = Spinner(this).apply {
            adapter = ArrayAdapter(this@LocalGenerateActivity, android.R.layout.simple_spinner_dropdown_item,
                listOf("Très proche (10)", "Équilibré (20)", "Plus libre (35)"))
            setSelection(1)
        }
        col.addView(strength)
        generate = col.button("Générer") {
            val pr = profiles[profile.selectedItemPosition]
            val (w, h) = LocalJobs.dims(formats[format.selectedItemPosition], pr.longSide)
            val userDesc = desc.text.toString().trim()
            App.prefs(this).edit().putString("local_desc", userDesc).apply()
            val prompt = "a photo of a ${subjects[subject.selectedItemPosition]} img, $userDesc, photograph, natural skin texture, " +
                "soft light, sharp focus, high detail"
            val params = JSONObject().put("refs", JSONArray(selected)).put("prompt", prompt).put("description", userDesc)
                .put("negative", "cartoon, painting, illustration, 3d render, deformed hands, extra fingers, distorted face, blurry, lowres, watermark, text, nsfw, nude")
                .put("width", w).put("height", h).put("steps", pr.steps).put("cfg", 1.8).put("threads", pr.threads)
                .put("profile", pr.id).put("style_strength", strengths[strength.selectedItemPosition])
                .put("seed", seed.text.toString().toLongOrNull() ?: Random.nextLong(1, 2_147_483_647))
            val warn = memoryWarning()
            val go: () -> Unit = {
                if (!GenerationService.start(this, GenerationService.TASK_GENERATE, params)) {
                    stage.text = "Une tâche est déjà en cours."
                }
            }
            if (warn != null) AlertDialog.Builder(this).setTitle("Attention").setMessage(warn)
                .setPositiveButton("Lancer quand même") { _, _ -> go() }.setNegativeButton("Annuler", null).show()
            else go()
        }
        cancel = col.button("Annuler la génération") { LocalJobs.cancel() }
        stage = col.label("", 15f, bold = true)
        col.button("Historique des générations") { startActivity(Intent(this, HistoryActivity::class.java)) }
        col.label("Durée : plusieurs minutes par image sur le processeur du téléphone. Le téléphone peut chauffer ; " +
            "la génération s'arrête d'elle-même si la température devient critique. Les références ne quittent jamais l'appareil.", 12f)
        if (Build.VERSION.SDK_INT >= 33) requestPermissions(arrayOf("android.permission.POST_NOTIFICATIONS"), 1)
        selected = App.library(this).selectForEngine("face", 4).map { it.sha256 }.toMutableList()
    }

    private fun memoryWarning(): String? {
        val mi = ActivityManager.MemoryInfo()
        (getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager).getMemoryInfo(mi)
        val totalGb = mi.totalMem / 1e9
        val availGb = mi.availMem / 1e9
        return when {
            totalGb < 7.5 -> "Cet appareil a %.1f Go de RAM ; le moteur en a besoin d'environ 5,5 Go. Échec probable.".format(totalGb)
            availGb < 5.5 -> "Seulement %.1f Go de mémoire libre (≈ 5,5 Go nécessaires). Fermez d'autres applications.".format(availGb)
            LocalJobs.thermalStatus(this) >= 2 -> "L'appareil est déjà chaud ; la génération risque d'être interrompue."
            else -> null
        }
    }

    private fun chooseRefs() {
        val refs = App.library(this).all().filter { it.authorized }
        if (refs.isEmpty()) { stage.text = "Importez d'abord des références autorisées."; return }
        val names = refs.map { "${Library.REFERENCE_VIEWS.firstOrNull { v -> v == it.view } ?: it.view} · ${it.sourceName}" }.toTypedArray()
        val checked = refs.map { it.sha256 in selected }.toBooleanArray()
        AlertDialog.Builder(this).setTitle("Références (4 au maximum)")
            .setMultiChoiceItems(names, checked) { _, i, c -> checked[i] = c }
            .setPositiveButton("OK") { _, _ ->
                selected = refs.filterIndexed { i, _ -> checked[i] }.take(4).map { it.sha256 }.toMutableList()
                updateChecks()
            }.show()
    }

    private fun updateChecks() {
        val store = LocalJobs.store(this)
        val engineOk = LocalJobs.binary(this).isFile
        val problems = mutableListOf<String>()
        if (!engineOk) problems += "moteur natif absent de cette APK"
        if (!store.ready()) problems += "modèle non installé (Accueil → Modèle local)"
        if (selected.isEmpty()) problems += "aucune référence choisie"
        if (store.freeBytes() < 200L * 1_048_576) problems += "stockage presque plein"
        checks.text = if (problems.isEmpty()) "Prêt : moteur, modèle et références présents." else "Impossible de générer : " + problems.joinToString(" ; ")
        checks.setTextColor(if (problems.isEmpty()) Color.rgb(0, 110, 0) else Color.rgb(170, 60, 0))
        generate.isEnabled = problems.isEmpty() && !LocalJobs.status.running
        refsLabel.text = "Références choisies : ${selected.size}"
        refsView.removeAllViews()
        val lib = App.library(this)
        selected.mapNotNull { lib.get(it) }.forEach { r ->
            val iv = ImageView(this).apply { scaleType = ImageView.ScaleType.CENTER_CROP }
            iv.setImageBitmap(BitmapFactory.decodeFile(lib.fileFor(r).path, BitmapFactory.Options().apply { inSampleSize = 8 }))
            refsView.addView(iv, LinearLayout.LayoutParams(dp(72), dp(72)).apply { marginEnd = dp(6) })
        }
    }

    private fun render(s: LocalJobs.Status) {
        val stepTxt = if (s.totalSteps > 0) " — pas ${s.step}/${s.totalSteps}" else ""
        stage.setTextColor(if (s.error != null) Color.RED else Color.DKGRAY)
        stage.text = when {
            s.error != null -> s.error
            s.running && s.kind == "generate" -> "Étape : ${s.stage}$stepTxt" + (if (s.message.isNotEmpty()) "\n${s.message}" else "")
            s.running -> "Autre tâche en cours : ${s.stage}"
            s.resultId != null && s.kind == "generate" -> "Image générée ✓ (voir l'historique)"
            else -> ""
        }
        cancel.isEnabled = s.running
        updateChecks()
        if (!s.running && s.resultId != null && s.kind == "generate" && s.error == null)
            startActivity(Intent(this, HistoryActivity::class.java).putExtra("open", s.resultId))
                .also { LocalJobs.update(s.copy(resultId = null)) }
    }

    override fun onResume() { super.onResume(); updateChecks(); LocalJobs.listen(listener) }
    override fun onPause() { LocalJobs.unlisten(listener); super.onPause() }
}

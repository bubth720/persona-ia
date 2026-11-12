package ia.persona.app.ui

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.text.InputType
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.RadioButton
import android.widget.RadioGroup
import android.widget.Spinner
import android.widget.TextView
import ia.persona.app.engine.EngineClient
import org.json.JSONObject
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/** Génération : visage/corps, tenue, graine ; lancer, suivre, annuler, reprendre. */
class GenerateActivity : Activity() {
    private val io = Executors.newSingleThreadExecutor()
    private val polling = AtomicBoolean(false)
    private lateinit var out: TextView
    private lateinit var launch: Button
    private lateinit var cancel: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val col = screen("Générer une planche")
        val engine = App.engine(this)
        col.label(if (engine == null) "Aucun moteur configuré : renseignez-le dans Réglages." else "Moteur : ${engine.base}", 14f)
        val kind = RadioGroup(this).apply { orientation = RadioGroup.HORIZONTAL }
        val face = RadioButton(this).apply { text = "Planche faciale (6 vues)"; id = 1; isChecked = true }
        val body = RadioButton(this).apply { text = "Planche corporelle (4 vues)"; id = 2 }
        kind.addView(face); kind.addView(body)
        col.addView(kind)
        col.label("Sujet", 14f)
        val subjects = listOf("woman", "man", "person")
        val subject = Spinner(this).apply {
            adapter = ArrayAdapter(this@GenerateActivity, android.R.layout.simple_spinner_dropdown_item,
                listOf("femme", "homme", "personne"))
        }
        col.addView(subject)
        val appearance = EditText(this).apply {
            hint = "Tenue / coiffure verrouillées (anglais conseillé)"
            setText(App.prefs(this@GenerateActivity).getString("appearance", "plain fitted grey t-shirt, dark jeans, white sneakers"))
        }
        col.addView(appearance)
        val seed = EditText(this).apply { hint = "Graine (vide = aléatoire)"; inputType = InputType.TYPE_CLASS_NUMBER }
        col.addView(seed)
        launch = col.button("Lancer la génération") {
            val e = App.engine(this) ?: return@button show("Moteur non configuré.", true)
            if (!App.transferConsent(this))
                return@button show("Transfert refusé : activez le consentement de transfert vers le moteur dans Réglages.", true)
            val k = if (kind.checkedRadioButtonId == 2) "body" else "face"
            App.prefs(this).edit().putString("appearance", appearance.text.toString()).apply()
            val params = JSONObject().put("subject_class", subjects[subject.selectedItemPosition])
                .put("appearance", appearance.text.toString())
            submit(e, k, seed.text.toString().toLongOrNull(), params)
        }
        cancel = col.button("Annuler le job en cours") {
            val id = App.prefs(this).getString("current_job", null) ?: return@button
            val e = App.engine(this) ?: return@button
            io.execute {
                try { e.cancelJob(id); ui { show("Annulé. Les vues terminées sont conservées ; relancer = reprise.", false) } }
                catch (ex: Exception) { ui { show("Annulation impossible : ${ex.message}", true) } }
            }
        }
        col.button("Reprendre le job en cours") {
            val id = App.prefs(this).getString("current_job", null) ?: return@button show("Aucun job en cours.", true)
            val e = App.engine(this) ?: return@button
            io.execute {
                try { e.start(id); poll(e, id) } catch (ex: Exception) { ui { show("Reprise impossible : ${ex.message}", true) } }
            }
        }
        col.button("Voir les résultats") { startActivity(Intent(this, ResultsActivity::class.java)) }
        out = col.label("", 14f)
    }

    override fun onResume() {
        super.onResume()
        val id = App.prefs(this).getString("current_job", null)
        val e = App.engine(this)
        if (id != null && e != null && polling.compareAndSet(false, true)) io.execute { try { poll(e, id) } finally { polling.set(false) } }
    }

    private fun show(msg: String, error: Boolean) {
        out.setTextColor(if (error) Color.RED else Color.DKGRAY)
        out.text = msg
    }

    private fun submit(e: EngineClient, kind: String, seed: Long?, params: JSONObject) {
        val lib = App.library(this)
        val refs = lib.selectForEngine(kind)
        if (refs.isEmpty()) return show("Aucune référence autorisée dans la bibliothèque.", true)
        launch.isEnabled = false
        show("Création du job, envoi de ${refs.size} référence(s) autorisée(s)…", false)
        io.execute {
            try {
                val profile = App.prefs(this).getString("profile", "")?.ifBlank { "profil" } ?: "profil"
                val job = e.createJob(kind, seed, params, profile)
                val id = job.getString("id")
                App.prefs(this).edit().putString("current_job", id).apply()
                App.addJob(this, id)
                refs.forEachIndexed { i, r ->
                    e.uploadAuthorizedReference(id, r.sha256, lib.fileFor(r).readBytes())
                    ui { show("Référence ${i + 1}/${refs.size} envoyée", false) }
                }
                e.start(id)
                poll(e, id)
            } catch (ex: Exception) {
                ui { show("Échec : ${ex.message}", true) }
            } finally {
                ui { launch.isEnabled = true }
            }
        }
    }

    private fun poll(e: EngineClient, id: String) {
        try { pollLoop(e, id) } catch (_: InterruptedException) { }
    }

    private fun pollLoop(e: EngineClient, id: String) {
        var failures = 0
        while (!isFinishing && !isDestroyed) {
            val st = try { e.getStatus(id).also { failures = 0 } } catch (ex: Exception) {
                failures++
                ui { show("Moteur injoignable (${ex.message}). Nouvel essai… Le job continue côté moteur.", true) }
                if (failures > 30) return
                Thread.sleep(3000); continue
            }
            val views = st.getJSONObject("views")
            val lines = views.keys().asSequence().map { v ->
                val s = views.getJSONObject(v)
                "${VIEW_LABELS[v] ?: v} : ${s.getString("state")}" + (s.optString("error").takeIf { it.isNotBlank() }?.let { " ($it)" } ?: "")
            }.toList()
            val generative = st.optJSONObject("backend")?.optBoolean("is_generation", false) ?: false
            val state = st.getString("state")
            ui {
                show("Job ${id.take(8)} — $state\n" + lines.joinToString("\n") +
                    if (!generative) "\n\nATTENTION : moteur de test non génératif — images non valables comme résultat." else "",
                    !generative)
            }
            if (state in setOf("succeeded", "failed", "cancelled")) return
            Thread.sleep(2000)
        }
    }

    override fun onDestroy() { io.shutdownNow(); super.onDestroy() }
}

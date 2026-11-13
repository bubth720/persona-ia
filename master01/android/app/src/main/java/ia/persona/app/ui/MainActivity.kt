package ia.persona.app.ui

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.widget.EditText
import android.widget.LinearLayout

/** Accueil : un profil, Importer, Générer une planche, galerie des résultats. */
class MainActivity : Activity() {
    private lateinit var status: android.widget.TextView
    private lateinit var engineInfo: android.widget.TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val col = screen("PERSONA IA")
        col.label("PERSONA IA", 26f, bold = true, color = Color.BLACK)
        val prefs = App.prefs(this)
        val name = EditText(this).apply {
            hint = "Nom du profil (personne adulte consentante)"
            setText(prefs.getString("profile", ""))
            setOnFocusChangeListener { _, has -> if (!has) prefs.edit().putString("profile", text.toString()).apply() }
        }
        col.addView(name)
        status = col.label("")
        engineInfo = col.label("", 14f)
        col.button("Importer des photos") { startActivity(Intent(this, ReferencesActivity::class.java).putExtra("import", true)) }
        col.button("Références et couverture") { startActivity(Intent(this, ReferencesActivity::class.java)) }
        col.button("Générer sur le téléphone (local)") { startActivity(Intent(this, LocalGenerateActivity::class.java)) }
        col.button("Historique des générations") { startActivity(Intent(this, HistoryActivity::class.java)) }
        col.button("Modèle local (installation unique)") { startActivity(Intent(this, ModelActivity::class.java)) }
        col.label("Mode PC (futur)", 14f, bold = true)
        col.button("Planche via un moteur PC du réseau local") { startActivity(Intent(this, GenerateActivity::class.java)) }
        col.button("Résultats du moteur PC") { startActivity(Intent(this, ResultsActivity::class.java)) }
        col.button("Réglages et confidentialité") { startActivity(Intent(this, SettingsActivity::class.java)) }
        col.label("Tout fonctionne hors ligne une fois le modèle installé : la génération tourne sur le processeur " +
            "du téléphone (plusieurs minutes par image). Le mode PC est optionnel.", 13f)
    }

    override fun onResume() {
        super.onResume()
        val lib = App.library(this)
        val refs = lib.all()
        status.text = "${refs.size} références · ${refs.count { it.validated }} classées · ${App.jobs(this).size} générations"
        val url = App.prefs(this).getString("engine_url", "") ?: ""
        val ready = ia.persona.app.engine.LocalJobs.store(this).ready()
        engineInfo.text = (if (ready) "Moteur local : prêt (hors ligne)." else "Moteur local : modèle à installer (Modèle local).") +
            (if (url.isBlank()) "" else "\nMoteur PC configuré : $url")
        engineInfo.setTextColor(if (ready) Color.rgb(0, 110, 0) else Color.rgb(160, 60, 0))
    }
}

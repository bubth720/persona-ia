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
        col.button("Générer une planche") { startActivity(Intent(this, GenerateActivity::class.java)) }
        col.button("Résultats / galerie") { startActivity(Intent(this, ResultsActivity::class.java)) }
        col.button("Réglages et confidentialité") { startActivity(Intent(this, SettingsActivity::class.java)) }
        col.label("La bibliothèque fonctionne hors ligne. La génération photoréaliste exige un moteur GPU " +
            "(PC local ou GPU distant autorisé) : elle n'est pas exécutée sur le téléphone.", 13f)
    }

    override fun onResume() {
        super.onResume()
        val lib = App.library(this)
        val refs = lib.all()
        status.text = "${refs.size} références · ${refs.count { it.validated }} classées · ${App.jobs(this).size} générations"
        val url = App.prefs(this).getString("engine_url", "") ?: ""
        engineInfo.text = if (url.isBlank()) "Moteur : aucun — génération indisponible (bibliothèque seule)."
        else "Moteur : $url — dépendance à un calcul hors téléphone."
        engineInfo.setTextColor(if (url.isBlank()) Color.rgb(160, 60, 0) else Color.DKGRAY)
    }
}

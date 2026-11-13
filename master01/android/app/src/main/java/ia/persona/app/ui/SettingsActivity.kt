package ia.persona.app.ui

import android.app.Activity
import android.app.AlertDialog
import android.graphics.Color
import android.os.Bundle
import android.os.StatFs
import android.text.InputType
import android.widget.CheckBox
import android.widget.EditText
import ia.persona.app.engine.EngineClient
import java.util.concurrent.Executors

/** Réglages : moteur (PC local / GPU distant autorisé), consentement de transfert, stockage, effacement, diagnostic. */
class SettingsActivity : Activity() {
    private val io = Executors.newSingleThreadExecutor()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val col = screen("Réglages")
        val p = App.prefs(this)
        col.label("Moteur de génération", bold = true)
        val url = EditText(this).apply {
            hint = "https://… ou http://192.168.x.x:8765 (réseau local privé)"
            setText(p.getString("engine_url", ""))
            inputType = InputType.TYPE_TEXT_VARIATION_URI
        }
        col.addView(url)
        val token = EditText(this).apply {
            hint = "Jeton du moteur (fichier worker_token.txt)"
            setText(p.getString("engine_token", ""))
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
        }
        col.addView(token)
        val consent = CheckBox(this).apply {
            text = "J'autorise l'envoi des références sélectionnées vers ce moteur (calcul hors téléphone). " +
                "Vérifiez les conditions de l'hébergeur GPU avant toute photo réelle."
            isChecked = p.getBoolean("transfer_consent", false)
        }
        col.addView(consent)
        val diag = col.label("", 14f)
        col.button("Enregistrer et tester le moteur") {
            val u = url.text.toString().trim(); val t = token.text.toString().trim()
            try { if (u.isNotEmpty()) EngineClient.validateUrl(u) } catch (e: Exception) {
                diag.setTextColor(Color.RED); diag.text = e.message; return@button
            }
            p.edit().putString("engine_url", u).putString("engine_token", t).putBoolean("transfer_consent", consent.isChecked).apply()
            val e = App.engine(this) ?: run { diag.text = "Moteur non configuré (bibliothèque seule)."; return@button }
            diag.setTextColor(Color.DKGRAY); diag.text = "Test…"
            io.execute {
                val msg = try {
                    val h = e.health().getJSONObject("backend")
                    "OK : backend ${h.optString("name")} · génératif=${h.optBoolean("is_generation")}"
                } catch (x: Exception) { "Injoignable : ${x.message}" }
                ui { diag.text = msg }
            }
        }
        col.label("Stockage", bold = true)
        val lib = App.library(this)
        val used = lib.root.walkTopDown().filter { it.isFile }.sumOf { it.length() }
        val free = StatFs(filesDir.path).availableBytes
        col.label("Bibliothèque privée : ${used / 1_048_576} Mo · libre : ${free / 1_048_576} Mo · " +
            "pas de sauvegarde cloud (allowBackup=false) · export volontaire uniquement.", 13f)
        col.label("Données réseau : seules les références envoyées et les PNG reçus transitent ; rien n'est envoyé sans job lancé.", 13f)
        col.button("Effacer la bibliothèque privée…") {
            AlertDialog.Builder(this).setTitle("Effacer ?")
                .setMessage("Supprime les copies privées des références dans l'application. Vos fichiers originaux ne sont pas touchés.")
                .setPositiveButton("Effacer") { _, _ -> lib.wipe(); recreate() }
                .setNegativeButton("Annuler", null).show()
        }
        col.label("Version 2.0.0-master02 · minSdk 29 · génération locale : écran « Modèle local ».", 12f)
    }

    override fun onDestroy() { io.shutdown(); super.onDestroy() }
}

package ia.persona.app.ui

import android.app.Activity
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import ia.persona.app.data.Library
import ia.persona.app.engine.EngineClient
import java.io.File

/** Accès partagé : une seule bibliothèque, réglages, état du job courant. */
object App {
    @Volatile private var lib: Library? = null
    fun library(ctx: Context): Library = lib ?: synchronized(this) {
        lib ?: Library(File(ctx.applicationContext.filesDir, "library")).also { lib = it }
    }
    fun prefs(ctx: Context) = ctx.getSharedPreferences("persona", Context.MODE_PRIVATE)
    fun engine(ctx: Context): EngineClient? {
        val p = prefs(ctx)
        val url = p.getString("engine_url", "") ?: ""
        val token = p.getString("engine_token", "") ?: ""
        if (url.isBlank() || token.isBlank()) return null
        return try { EngineClient(url, token) } catch (_: Exception) { null }
    }
    fun transferConsent(ctx: Context) = prefs(ctx).getBoolean("transfer_consent", false)
    fun resultsDir(ctx: Context, jobId: String) = File(ctx.filesDir, "results/$jobId").apply { mkdirs() }
    fun jobs(ctx: Context): List<String> =
        (prefs(ctx).getString("jobs", "") ?: "").split(",").filter { it.isNotBlank() }
    fun addJob(ctx: Context, id: String) {
        val l = (listOf(id) + jobs(ctx).filter { it != id }).take(50)
        prefs(ctx).edit().putString("jobs", l.joinToString(",")).apply()
    }
}

val VIEW_LABELS = mapOf(
    "face" to "Face", "profil_gauche" to "Profil gauche", "profil_droit" to "Profil droit",
    "trois_quarts_gauche" to "Trois-quarts gauche", "trois_quarts_droit" to "Trois-quarts droit",
    "expression" to "Expression alternative", "pied_face" to "Plein pied — face",
    "pied_profil" to "Plein pied — profil", "pied_trois_quarts" to "Plein pied — trois-quarts",
    "pied_dos" to "Plein pied — dos (estimé)", "dos" to "Dos", "plan_americain" to "Plan américain",
    "plein_pied" to "Plein pied", "non_classe" to "Non classé",
)

fun Activity.screen(title: String): LinearLayout {
    this.title = title
    val col = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        val p = dp(16)
        setPadding(p, p, p, p)
    }
    setContentView(ScrollView(this).apply { addView(col) })
    return col
}

fun Context.dp(v: Int) = (v * resources.displayMetrics.density).toInt()

fun LinearLayout.label(text: String, size: Float = 16f, bold: Boolean = false, color: Int = Color.DKGRAY): TextView {
    val t = TextView(context).apply {
        this.text = text; textSize = size; setTextColor(color)
        if (bold) setTypeface(typeface, Typeface.BOLD)
        setPadding(0, context.dp(6), 0, context.dp(6))
    }
    addView(t)
    return t
}

fun LinearLayout.button(text: String, onClick: (View) -> Unit): Button {
    val b = Button(context).apply { this.text = text; isAllCaps = false; setOnClickListener(onClick) }
    addView(b, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
    return b
}

fun Activity.ui(block: () -> Unit) = runOnUiThread { if (!isFinishing && !isDestroyed) block() }

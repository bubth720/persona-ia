package ia.persona.app

import ia.persona.app.engine.ModelStore

/** Aide de test : télécharge un Spec depuis une URL locale (le Spec réel pointe vers huggingface.co). */
object TestSpec {
    data class Local(val spec: ModelStore.Spec, val url: String)
    fun withUrl(spec: ModelStore.Spec, url: String) = Local(spec, url)
    fun download(store: ModelStore, l: Local) = store.download(l.spec, { false }, { _, _ -> }, l.url)
}

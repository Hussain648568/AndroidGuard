package com.fyp.androidguard.services

import android.content.Context
import com.fyp.androidguard.models.AuditHistoryItem
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken

object AuditHistoryManager {

    private const val PREFS_NAME = "androidguard_audit_history"
    private const val KEY_HISTORY = "history_items"
    private val gson = Gson()

    fun getHistory(context: Context): List<AuditHistoryItem> {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        val json = prefs.getString(KEY_HISTORY, null) ?: return emptyList()
        return try {
            val type = object : TypeToken<List<AuditHistoryItem>>() {}.type
            gson.fromJson(json, type) ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun saveAudit(context: Context, item: AuditHistoryItem) {
        val current = getHistory(context).toMutableList()
        // Remove older audit for same package if present to avoid clutter, or prepend
        current.removeAll { it.packageName == item.packageName && it.sha256 == item.sha256 }
        current.add(0, item) // newest first

        // Keep last 50 audits
        val trimmed = if (current.size > 50) current.subList(0, 50) else current

        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(KEY_HISTORY, gson.toJson(trimmed)).apply()
    }

    fun clearHistory(context: Context) {
        val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
        prefs.edit().remove(KEY_HISTORY).apply()
    }
}

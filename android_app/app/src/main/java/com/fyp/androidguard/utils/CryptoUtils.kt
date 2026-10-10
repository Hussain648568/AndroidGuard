package com.fyp.androidguard.utils

import java.io.File
import java.security.MessageDigest

object CryptoUtils {
    /**
     * Efficiently streams and computes the cryptographic SHA-256 hash of a file.
     * Operates in O(N) stream time without loading large APKs into memory.
     */
    fun calculateFileSha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { inputStream ->
            val buffer = ByteArray(16384)
            var bytesRead: Int
            while (inputStream.read(buffer).also { bytesRead = it } != -1) {
                digest.update(buffer, 0, bytesRead)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}

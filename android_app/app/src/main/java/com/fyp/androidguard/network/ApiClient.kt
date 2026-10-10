package com.fyp.androidguard.network

import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {
    // Default emulator loopback alias
    private const val BASE_URL = "http://10.0.2.2:8080/"

    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(60, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(60, TimeUnit.SECONDS)
        .addInterceptor { chain ->
            val original = chain.request()
            try {
                chain.proceed(original)
            } catch (e: Exception) {
                // If 10.0.2.2 fails, seamlessly fall back to 127.0.0.1 (ADB reverse tunnel)
                val fallbackHost = if (original.url.host == "10.0.2.2") "127.0.0.1" else "10.0.2.2"
                val newUrl = original.url.newBuilder().host(fallbackHost).build()
                val fallbackRequest = original.newBuilder().url(newUrl).build()
                chain.proceed(fallbackRequest)
            }
        }
        .build()

    val instance: ApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}

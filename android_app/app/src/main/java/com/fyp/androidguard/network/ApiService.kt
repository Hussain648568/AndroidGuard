package com.fyp.androidguard.network

import com.fyp.androidguard.models.AnalyzeResponse
import com.fyp.androidguard.models.StatusResponse
import okhttp3.MultipartBody
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import okhttp3.ResponseBody

interface ApiService {
    @GET("/api/v1/cache/check/{sha256}")
    suspend fun checkCache(@Path("sha256") sha256: String): com.fyp.androidguard.models.CacheCheckResponse

    @Multipart
    @POST("/api/v1/analyze")
    suspend fun uploadApk(@Part file: MultipartBody.Part): AnalyzeResponse

    @GET("/api/v1/status/{run_id}")
    suspend fun getStatus(@Path("run_id") runId: String): StatusResponse

    @GET("/api/v1/report/{run_id}")
    suspend fun getReport(@Path("run_id") runId: String): ResponseBody
}

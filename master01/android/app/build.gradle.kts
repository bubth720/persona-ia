plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "ia.persona.app"
    compileSdk = 35
    defaultConfig {
        applicationId = "ia.persona.app"
        minSdk = 29
        targetSdk = 35
        versionCode = 200
        versionName = "2.0.0-master02"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }
    buildTypes {
        getByName("release") { isMinifyEnabled = false }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    testOptions { unitTests.isIncludeAndroidResources = false }
    // Le moteur natif (libsdcli.so, compilé par la CI depuis stable-diffusion.cpp épinglé) est un exécutable :
    // il doit être extrait dans nativeLibraryDir pour pouvoir être lancé dans un processus séparé.
    packaging { jniLibs { useLegacyPackaging = true } }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test:rules:1.6.1")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
}

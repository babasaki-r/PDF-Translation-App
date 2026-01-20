#!/usr/bin/env swift

// Apple Translation API を使用した翻訳スクリプト
// macOS 15 (Sequoia) 以降で動作
// オフラインでも動作（言語パックがダウンロード済みの場合）
// 使用方法: swift apple_translate.swift <input_file_path> [direction]
//   direction: "en-to-ja" (デフォルト) または "ja-to-en"

import Foundation
import Translation

@available(macOS 15.0, *)
func translateText(_ text: String, direction: String) async throws -> String {
    // 翻訳方向に応じて言語を設定
    let sourceLanguage: Locale.Language
    let targetLanguage: Locale.Language

    if direction == "ja-to-en" {
        // 日本語から英語
        sourceLanguage = Locale.Language(identifier: "ja")
        targetLanguage = Locale.Language(identifier: "en")
    } else {
        // 英語から日本語（デフォルト）
        sourceLanguage = Locale.Language(identifier: "en")
        targetLanguage = Locale.Language(identifier: "ja")
    }

    // 翻訳セッションを作成
    let session = TranslationSession(installedSource: sourceLanguage, target: targetLanguage)

    // タイムアウト付きで翻訳を実行（110秒、Swift側の115秒タイムアウトより短く）
    return try await withTimeout(seconds: 110) {
        let response = try await session.translate(text)
        return response.targetText
    }
}

@available(macOS 15.0, *)
func withTimeout<T>(seconds: TimeInterval, operation: @escaping () async throws -> T) async throws -> T {
    return try await withThrowingTaskGroup(of: T.self) { group in
        // メインタスク
        group.addTask {
            return try await operation()
        }
        
        // タイムアウトタスク
        group.addTask {
            try await Task.sleep(nanoseconds: UInt64(seconds * 1_000_000_000))
            throw NSError(domain: "AppleTranslate", code: 3, userInfo: [NSLocalizedDescriptionKey: "Translation timed out after \(Int(seconds)) seconds"])
        }
        
        // 最初に完了したタスクの結果を返す（成功またはタイムアウト）
        let result = try await group.next()!
        group.cancelAll()
        return result
    }
}

@available(macOS 15.0, *)
func main() async throws {
    // コマンドライン引数からファイルパスと翻訳方向を取得
    let arguments = CommandLine.arguments

    guard arguments.count > 1 else {
        throw NSError(domain: "AppleTranslate", code: 1, userInfo: [NSLocalizedDescriptionKey: "No input file provided"])
    }

    let inputPath = arguments[1]
    let direction = arguments.count > 2 ? arguments[2] : "en-to-ja"

    // ファイルからテキストを読み込む
    let textToTranslate: String
    do {
        textToTranslate = try String(contentsOfFile: inputPath, encoding: .utf8)
    } catch {
        throw NSError(domain: "AppleTranslate", code: 2, userInfo: [NSLocalizedDescriptionKey: "Error reading file: \(error.localizedDescription)"])
    }

    // 空のテキストはスキップ
    guard !textToTranslate.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
        print("")
        return
    }

    let translatedText = try await translateText(textToTranslate, direction: direction)
    print(translatedText)
}

// macOS バージョンチェック
if #available(macOS 15.0, *) {
    // 非同期で実行
    let semaphore = DispatchSemaphore(value: 0)
    var exitCode: Int32 = 0

    Task {
        do {
            try await main()
        } catch {
            fputs("Translation error: \(error.localizedDescription)\n", stderr)
            exitCode = 1
        }
        // 常にセマフォをシグナル（成功・失敗に関わらず）
        semaphore.signal()
    }

    // タイムアウト付きで待機（初回は115秒、リトライ時は175秒、Python側のタイムアウトより短く）
    let timeout = DispatchTime.now() + .seconds(115)
    let result = semaphore.wait(timeout: timeout)
    
    if result == .timedOut {
        fputs("Error: Translation timed out after 110 seconds\n", stderr)
        exit(1)
    }
    
    // エラーが発生していた場合は終了
    if exitCode != 0 {
        exit(exitCode)
    }
} else {
    fputs("Error: macOS 15.0 or later is required for Apple Translation API\n", stderr)
    exit(1)
}

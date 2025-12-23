#!/usr/bin/env swift

// Apple Translation API を使用した翻訳スクリプト
// macOS 15 (Sequoia) 以降で動作
// オフラインでも動作（言語パックがダウンロード済みの場合）
// 使用方法: swift apple_translate.swift <input_file_path>

import Foundation
import Translation

@available(macOS 15.0, *)
func translateText(_ text: String) async throws -> String {
    // 英語から日本語への翻訳設定
    let sourceLanguage = Locale.Language(identifier: "en")
    let targetLanguage = Locale.Language(identifier: "ja")

    // 翻訳セッションを作成
    let session = TranslationSession(installedSource: sourceLanguage, target: targetLanguage)

    // 翻訳を実行
    let response = try await session.translate(text)

    return response.targetText
}

@available(macOS 15.0, *)
func main() async {
    // コマンドライン引数からファイルパスを取得
    let arguments = CommandLine.arguments

    guard arguments.count > 1 else {
        fputs("Error: No input file provided\n", stderr)
        exit(1)
    }

    let inputPath = arguments[1]

    // ファイルからテキストを読み込む
    let textToTranslate: String
    do {
        textToTranslate = try String(contentsOfFile: inputPath, encoding: .utf8)
    } catch {
        fputs("Error reading file: \(error.localizedDescription)\n", stderr)
        exit(1)
    }

    // 空のテキストはスキップ
    guard !textToTranslate.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
        print("")
        exit(0)
    }

    do {
        let translatedText = try await translateText(textToTranslate)
        print(translatedText)
    } catch {
        fputs("Translation error: \(error.localizedDescription)\n", stderr)
        exit(1)
    }
}

// macOS バージョンチェック
if #available(macOS 15.0, *) {
    // 非同期で実行
    let semaphore = DispatchSemaphore(value: 0)

    Task {
        await main()
        semaphore.signal()
    }

    semaphore.wait()
} else {
    fputs("Error: macOS 15.0 or later is required for Apple Translation API\n", stderr)
    exit(1)
}

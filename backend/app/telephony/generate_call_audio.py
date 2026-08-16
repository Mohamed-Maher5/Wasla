# This script pre-generates the fixed telephony MP3 prompts used by Vonage streams.

from app.telephony.tts import generate_audio


PROMPTS = [
    (
        "ask_question.mp3",
        "مساء الخير يا فندم، كنت بسأل حضرتك هل المشكلة اتحلت ولا لسه؟",
    ),
    (
        "resolved_thanks.mp3",
        "تمام يا فندم، شكرا لحضرتك ونتمنى لك يوم سعيد.",
    ),
    (
        "not_resolved_closing.mp3",
        "خلاص هقفل معاك دلوقتي وحد من الـ agents هيتواصل معاك",
    ),
    (
        "redirect_off_topic.mp3",
        "احنا بنتكلم بخصوص المشكلة، حضرتك تقدر تقولي اتحلت ولا لسه؟",
    ),
    (
        "repeat_unclear.mp3",
        "معلش، مسمعتش حضرتك كويس، ممكن تقول تاني؟",
    ),
]


def main() -> None:
    for filename, text in PROMPTS:
        generated = generate_audio(text, filename)
        print(generated)


if __name__ == "__main__":
    main()

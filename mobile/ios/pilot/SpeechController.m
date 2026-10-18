#import "SpeechController.h"
#import <AVFoundation/AVFoundation.h>
#import <Speech/Speech.h>
#import <UIKit/UIKit.h>

@interface RCSpeechController () <AVSpeechSynthesizerDelegate>
@property(nonatomic, strong) AVSpeechSynthesizer *synthesizer;
@property(nonatomic, strong, nullable) AVSpeechUtterance *utterance;
@property(nonatomic, copy, nullable) NSString *speechToken;
@property(nonatomic, strong) SFSpeechRecognizer *recognizer;
@property(nonatomic, strong, nullable) AVAudioEngine *engine;
@property(nonatomic, strong, nullable) SFSpeechAudioBufferRecognitionRequest *request;
@property(nonatomic, strong, nullable) SFSpeechRecognitionTask *task;
@property(nonatomic, copy, nullable) NSString *dictationToken;
@property(nonatomic, copy) NSString *lastText;
@property(nonatomic) NSUInteger generation;
@property(nonatomic) BOOL tapInstalled;
@property(nonatomic) BOOL recording;
@end

@implementation RCSpeechController
- (instancetype)init {
    if ((self = [super init])) {
        _synthesizer = [AVSpeechSynthesizer new];
        _synthesizer.delegate = self;
        _recognizer = [[SFSpeechRecognizer alloc] initWithLocale:[NSLocale localeWithLocaleIdentifier:@"fr-FR"]];
        _recognizer.queue = NSOperationQueue.mainQueue;
        _lastText = @"";
        [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(audioInterrupted:)
            name:AVAudioSessionInterruptionNotification object:nil];
        [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(routeChanged:)
            name:AVAudioSessionRouteChangeNotification object:nil];
    }
    return self;
}
- (void)dealloc { [NSNotificationCenter.defaultCenter removeObserver:self]; }
- (void)emit:(NSString *)kind status:(NSString *)status token:(NSString *)token text:(NSString *)text {
    if (self.eventSink && token) self.eventSink(@{@"kind":kind, @"status":status, @"token":token, @"text":text ?: @""});
}
- (AVSpeechSynthesisVoice *)frenchVoice {
    AVSpeechSynthesisVoice *fallback = nil;
    for (AVSpeechSynthesisVoice *voice in AVSpeechSynthesisVoice.speechVoices) {
        if (voice.voiceTraits & (AVSpeechSynthesisVoiceTraitIsPersonalVoice | AVSpeechSynthesisVoiceTraitIsNoveltyVoice)) continue;
        if ([voice.language isEqualToString:@"fr-FR"]) {
            if (!fallback || voice.quality > fallback.quality) fallback = voice;
        }
    }
    return fallback;
}
- (void)stopSpeaking {
    NSString *token = self.speechToken;
    self.speechToken = nil; self.utterance = nil;
    [self.synthesizer stopSpeakingAtBoundary:AVSpeechBoundaryImmediate];
    if (token) {
        [self emit:@"speech" status:@"stopped" token:token text:@""];
        if (!self.dictationToken) [AVAudioSession.sharedInstance setActive:NO withOptions:AVAudioSessionSetActiveOptionNotifyOthersOnDeactivation error:nil];
    }
}
- (void)stopCapture {
    [self.engine stop];
    if (self.tapInstalled) { [self.engine.inputNode removeTapOnBus:0]; self.tapInstalled = NO; }
    [self.request endAudio];
    self.recording = NO;
}
- (void)finishDictation:(NSString *)status {
    NSString *token = self.dictationToken;
    self.generation += 1; self.dictationToken = nil;
    [self stopCapture];
    [self.task cancel]; self.task = nil; self.request = nil; self.engine = nil;
    if (token) [self emit:@"dictation" status:status token:token text:self.lastText];
    [AVAudioSession.sharedInstance setActive:NO withOptions:AVAudioSessionSetActiveOptionNotifyOthersOnDeactivation error:nil];
}
- (void)cancelAll {
    [self stopSpeaking]; [self finishDictation:@"cancelled"];
}
- (void)interruptIfRunning {
    if (self.recording || self.task || self.speechToken) [self cancelAll];
}
- (void)audioInterrupted:(NSNotification *)notification {
    if ([notification.userInfo[AVAudioSessionInterruptionTypeKey] unsignedIntegerValue] == AVAudioSessionInterruptionTypeBegan)
        dispatch_async(dispatch_get_main_queue(), ^{ [self cancelAll]; });
}
- (void)routeChanged:(NSNotification *)notification {
    if ([notification.userInfo[AVAudioSessionRouteChangeReasonKey] unsignedIntegerValue] == AVAudioSessionRouteChangeReasonOldDeviceUnavailable)
        dispatch_async(dispatch_get_main_queue(), ^{ [self cancelAll]; });
}
- (void)beginCapture:(NSUInteger)generation {
    if (generation != self.generation || !self.dictationToken) return;
    if (UIApplication.sharedApplication.applicationState != UIApplicationStateActive || !self.recognizer.supportsOnDeviceRecognition) {
        [self finishDictation:@"unavailable"]; return;
    }
    NSError *error = nil;
    AVAudioSession *audio = AVAudioSession.sharedInstance;
    if (![audio setCategory:AVAudioSessionCategoryPlayAndRecord mode:AVAudioSessionModeMeasurement
                   options:AVAudioSessionCategoryOptionDefaultToSpeaker | AVAudioSessionCategoryOptionAllowBluetoothHFP error:&error] ||
        ![audio setActive:YES error:&error]) { [self finishDictation:@"unavailable"]; return; }
    self.engine = [AVAudioEngine new];
    AVAudioInputNode *input = self.engine.inputNode;
    AVAudioFormat *format = [input outputFormatForBus:0];
    if (!format.channelCount || format.sampleRate <= 0) { [self finishDictation:@"unavailable"]; return; }
    SFSpeechAudioBufferRecognitionRequest *request = [SFSpeechAudioBufferRecognitionRequest new];
    request.requiresOnDeviceRecognition = YES;
    request.shouldReportPartialResults = YES;
    request.taskHint = SFSpeechRecognitionTaskHintDictation;
    // Aucun mot attendu, modèle de réponse ou correction n'est fourni au reconnaisseur.
    request.contextualStrings = @[];
    self.request = request;
    __weak RCSpeechController *weakSelf = self;
    self.task = [self.recognizer recognitionTaskWithRequest:request resultHandler:^(SFSpeechRecognitionResult *result, NSError *failure) {
        dispatch_async(dispatch_get_main_queue(), ^{
            RCSpeechController *strong = weakSelf;
            if (!strong || generation != strong.generation || !strong.dictationToken) return;
            if (result) {
                NSString *text = result.bestTranscription.formattedString;
                strong.lastText = text.length > 2000 ? [text substringToIndex:2000] : text;
                [strong emit:@"dictation" status:strong.recording ? @"partial" : @"finishing" token:strong.dictationToken text:strong.lastText];
            }
            if (result.isFinal || failure) [strong finishDictation:failure ? @"interrupted" : @"finished"];
        });
    }];
    @try {
        [input installTapOnBus:0 bufferSize:1024 format:format block:^(AVAudioPCMBuffer *buffer, AVAudioTime *when) {
            [request appendAudioPCMBuffer:buffer];
        }];
        self.tapInstalled = YES;
        [self.engine prepare];
        if (![self.engine startAndReturnError:&error]) { [self finishDictation:@"unavailable"]; return; }
    } @catch (NSException *exception) { [self finishDictation:@"unavailable"]; return; }
    self.recording = YES;
    [self emit:@"dictation" status:@"listening" token:self.dictationToken text:@""];
    // Une capture courte ne reste jamais ouverte indéfiniment.
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 45 * NSEC_PER_SEC), dispatch_get_main_queue(), ^{
        if (generation == self.generation && self.dictationToken) [self stopDictation];
    });
}
- (void)stopDictation {
    if (!self.dictationToken) return;
    if (!self.recording) { [self finishDictation:@"cancelled"]; return; }
    [self stopCapture];
    [self emit:@"dictation" status:@"finishing" token:self.dictationToken text:self.lastText];
    NSUInteger generation = self.generation;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 2 * NSEC_PER_SEC), dispatch_get_main_queue(), ^{
        if (generation == self.generation && self.dictationToken) [self finishDictation:@"finished"];
    });
}
- (void)handle:(NSDictionary *)command reply:(void (^)(id, NSString *))reply {
    NSAssert(NSThread.isMainThread, @"Audio sur le thread principal");
    NSString *operation = command[@"operation"];
    NSString *token = command[@"token"];
    if (![operation isKindOfClass:NSString.class]) { reply(nil, @"Commande audio invalide."); return; }
    if ([operation isEqualToString:@"capabilities"]) {
        reply(@{@"speech":([self frenchVoice] ? @YES : @NO), @"on_device_dictation":(self.recognizer.supportsOnDeviceRecognition ? @YES : @NO)}, nil); return;
    }
    if ([operation isEqualToString:@"cancel"]) { [self cancelAll]; reply(@{@"ok":@YES}, nil); return; }
    if ([operation isEqualToString:@"stop-speaking"]) { [self stopSpeaking]; reply(@{@"ok":@YES}, nil); return; }
    if ([operation isEqualToString:@"stop-dictation"]) { [self stopDictation]; reply(@{@"ok":@YES}, nil); return; }
    if (![token isKindOfClass:NSString.class] || !token.length || token.length > 200) { reply(nil, @"Commande audio invalide."); return; }
    if ([operation isEqualToString:@"speak"]) {
        NSString *text = command[@"text"];
        AVSpeechSynthesisVoice *voice = [self frenchVoice];
        if (![text isKindOfClass:NSString.class] || !text.length || text.length > 12000 || !voice) {
            reply(nil, @"La lecture française est indisponible sur cet appareil."); return;
        }
        [self cancelAll];
        NSError *error = nil;
        if (![AVAudioSession.sharedInstance setCategory:AVAudioSessionCategoryPlayback mode:AVAudioSessionModeSpokenAudio options:AVAudioSessionCategoryOptionDuckOthers error:&error] ||
            ![AVAudioSession.sharedInstance setActive:YES error:&error]) { reply(nil, @"La lecture est indisponible pour le moment."); return; }
        self.speechToken = token;
        self.utterance = [AVSpeechUtterance speechUtteranceWithString:text];
        self.utterance.voice = voice; self.utterance.rate = AVSpeechUtteranceDefaultSpeechRate;
        [self.synthesizer speakUtterance:self.utterance]; reply(@{@"ok":@YES}, nil); return;
    }
    if ([operation isEqualToString:@"start-dictation"]) {
        [self cancelAll];
        if (!self.recognizer.supportsOnDeviceRecognition) { reply(nil, @"La dictée hors connexion en français n’est pas disponible. Tu peux utiliser le clavier."); return; }
        self.dictationToken = token; self.lastText = @"";
        NSUInteger generation = self.generation;
        [SFSpeechRecognizer requestAuthorization:^(SFSpeechRecognizerAuthorizationStatus status) {
            dispatch_async(dispatch_get_main_queue(), ^{
                if (generation != self.generation || !self.dictationToken) return;
                if (status != SFSpeechRecognizerAuthorizationStatusAuthorized) { [self finishDictation:@"denied"]; return; }
                [AVAudioApplication requestRecordPermissionWithCompletionHandler:^(BOOL granted) {
                    dispatch_async(dispatch_get_main_queue(), ^{
                        if (generation != self.generation || !self.dictationToken) return;
                        if (!granted) { [self finishDictation:@"denied"]; return; }
                        [self beginCapture:generation];
                    });
                }];
            });
        }];
        reply(@{@"ok":@YES}, nil); return;
    }
    reply(nil, @"Commande audio inconnue.");
}
- (void)speechSynthesizer:(AVSpeechSynthesizer *)synthesizer didStartSpeechUtterance:(AVSpeechUtterance *)utterance {
    if (utterance == self.utterance) [self emit:@"speech" status:@"speaking" token:self.speechToken text:@""];
}
- (void)speechSynthesizer:(AVSpeechSynthesizer *)synthesizer didCancelSpeechUtterance:(AVSpeechUtterance *)utterance {
    if (utterance == self.utterance) [self stopSpeaking];
}
- (void)speechSynthesizer:(AVSpeechSynthesizer *)synthesizer didFinishSpeechUtterance:(AVSpeechUtterance *)utterance {
    if (utterance != self.utterance) return;
    NSString *token = self.speechToken; self.speechToken = nil; self.utterance = nil;
    [self emit:@"speech" status:@"finished" token:token text:@""];
    [AVAudioSession.sharedInstance setActive:NO withOptions:AVAudioSessionSetActiveOptionNotifyOthersOnDeactivation error:nil];
}
@end

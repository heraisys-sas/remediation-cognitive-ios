// Pilote autonome : transport natif vers Python, aucun serveur HTTP.
#import "SceneDelegate.h"
#import "SpeechController.h"
#import "SemanticBridge.h"
#import <WebKit/WebKit.h>
#import <Python/Python.h>

static dispatch_queue_t EngineQueue;
static PyObject *EngineInstance;
static BOOL EngineAttempted;

static void PrepareQueue(void) {
    static dispatch_once_t once;
    dispatch_once(&once, ^{ EngineQueue = dispatch_queue_create("fr.heraisys.remediation.engine", DISPATCH_QUEUE_SERIAL); });
}

static BOOL PrepareEngine(void) {
    if (EngineInstance) return YES;
    if (EngineAttempted) return NO;
    EngineAttempted = YES;
    if (PyImport_AppendInittab("_rc_semantics", PyInit__rc_semantics) < 0) return NO;
    NSString *resources = NSBundle.mainBundle.resourcePath;
    PyPreConfig pre;
    PyPreConfig_InitIsolatedConfig(&pre);
    pre.utf8_mode = 1;
    PyStatus status = Py_PreInitialize(&pre);
    if (PyStatus_Exception(status)) return NO;
    PyConfig config;
    PyConfig_InitIsolatedConfig(&config);
    config.write_bytecode = 0;
    config.install_signal_handlers = 0;
    status = PyConfig_SetBytesString(&config, &config.home,
        [[resources stringByAppendingPathComponent:@"python"] UTF8String]);
    if (!PyStatus_Exception(status)) status = Py_InitializeFromConfig(&config);
    PyConfig_Clear(&config);
    if (PyStatus_Exception(status)) return NO;
    PyObject *paths = PySys_GetObject("path");
    for (NSString *folder in @[@"app_packages", @"app"]) {
        PyObject *path = PyUnicode_FromString([[resources stringByAppendingPathComponent:folder] UTF8String]);
        if (!path || PyList_Insert(paths, 0, path) < 0) {
            Py_XDECREF(path); PyErr_Print(); PyEval_SaveThread(); return NO;
        }
        Py_DECREF(path);
    }
    NSURL *base = [NSFileManager.defaultManager URLsForDirectory:NSApplicationSupportDirectory
                                                     inDomains:NSUserDomainMask].firstObject;
    NSURL *storage = [base URLByAppendingPathComponent:@"RemediationPilot" isDirectory:YES];
    NSError *error = nil;
    [NSFileManager.defaultManager createDirectoryAtURL:storage withIntermediateDirectories:YES
        attributes:@{NSFileProtectionKey: NSFileProtectionCompleteUntilFirstUserAuthentication} error:&error];
    if (error) { PyEval_SaveThread(); return NO; }
    [storage setResourceValue:@YES forKey:NSURLIsExcludedFromBackupKey error:nil];
    PyObject *module = PyImport_ImportModule("mobile.application_runtime");
    PyObject *type = module ? PyObject_GetAttrString(module, "ApplicationRuntime") : NULL;
    EngineInstance = type ? PyObject_CallFunction(type, "s", storage.path.UTF8String) : NULL;
    Py_XDECREF(type); Py_XDECREF(module);
    if (!EngineInstance) PyErr_Print();
    PyEval_SaveThread();
    return EngineInstance != NULL;
}

@interface PilotViewController : UIViewController <WKScriptMessageHandlerWithReply, WKNavigationDelegate>
@property(nonatomic, strong) WKWebView *web;
@property(nonatomic, strong) RCSpeechController *speech;
@property(nonatomic, copy) NSString *allowedRoot;
@end

@implementation PilotViewController
- (void)viewDidLoad {
    [super viewDidLoad];
    PrepareQueue();
    WKWebViewConfiguration *configuration = [[WKWebViewConfiguration alloc] init];
    [configuration.userContentController addScriptMessageHandlerWithReply:self
        contentWorld:WKContentWorld.pageWorld name:@"runtime"];
    [configuration.userContentController addScriptMessageHandlerWithReply:self
        contentWorld:WKContentWorld.pageWorld name:@"speech"];
    self.speech = [RCSpeechController new];
    __weak PilotViewController *weakSelf = self;
    self.speech.eventSink = ^(NSDictionary *event) {
        NSData *data = [NSJSONSerialization dataWithJSONObject:event options:0 error:nil];
        if (!data) return;
        NSString *json = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
        [weakSelf.web evaluateJavaScript:[NSString stringWithFormat:@"window.nativeSpeechEvent?.(%@)", json] completionHandler:nil];
    };
    self.web = [[WKWebView alloc] initWithFrame:CGRectZero configuration:configuration];
    self.web.navigationDelegate = self;
    self.web.translatesAutoresizingMaskIntoConstraints = NO;
    self.web.opaque = NO;
    self.web.backgroundColor = UIColor.systemBackgroundColor;
    self.view.backgroundColor = UIColor.systemBackgroundColor;
    [self.view addSubview:self.web];
    [NSLayoutConstraint activateConstraints:@[
        [self.web.topAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.topAnchor],
        [self.web.bottomAnchor constraintEqualToAnchor:self.view.safeAreaLayoutGuide.bottomAnchor],
        [self.web.leadingAnchor constraintEqualToAnchor:self.view.leadingAnchor],
        [self.web.trailingAnchor constraintEqualToAnchor:self.view.trailingAnchor]]];
    NSURL *directory = [NSBundle.mainBundle.resourceURL URLByAppendingPathComponent:@"pilot" isDirectory:YES];
    directory = directory.URLByResolvingSymlinksInPath.URLByStandardizingPath;
    self.allowedRoot = [directory.path stringByAppendingString:@"/"];
    [self.web loadFileURL:[directory URLByAppendingPathComponent:@"index.html"] allowingReadAccessToURL:directory];
}

- (void)webView:(WKWebView *)webView decidePolicyForNavigationAction:(WKNavigationAction *)action
 decisionHandler:(void (^)(WKNavigationActionPolicy))decisionHandler {
    NSURL *url = action.request.URL;
    BOOL allowed = [self isAllowedLocalURL:url];
    decisionHandler(allowed ? WKNavigationActionPolicyAllow : WKNavigationActionPolicyCancel);
}

- (BOOL)isAllowedLocalURL:(NSURL *)url {
    // Sur appareil, WebKit et NSBundle peuvent nommer le même dossier via
    // /var ou /private/var. Comparer leurs chemins résolus, tout en refusant
    // les liens qui sortent du dossier des ressources autorisées.
    return url.isFileURL && [url.URLByResolvingSymlinksInPath.URLByStandardizingPath.path hasPrefix:self.allowedRoot];
}

- (void)userContentController:(WKUserContentController *)controller didReceiveScriptMessage:(WKScriptMessage *)message
 replyHandler:(void (^)(id _Nullable, NSString * _Nullable))replyHandler {
    NSURL *origin = message.frameInfo.request.URL;
    if (!message.frameInfo.isMainFrame || ![self isAllowedLocalURL:origin] ||
        ![message.body isKindOfClass:NSDictionary.class]) {
        replyHandler(nil, @"Appel local refusé."); return;
    }
    NSError *encodingError = nil;
    NSData *data = [NSJSONSerialization dataWithJSONObject:message.body options:0 error:&encodingError];
    if (!data || data.length > 65536) { replyHandler(nil, @"Demande invalide."); return; }
    if ([message.name isEqualToString:@"speech"]) {
        [self.speech handle:message.body reply:replyHandler]; return;
    }
    NSString *request = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
    dispatch_async(EngineQueue, ^{
        if (!PrepareEngine()) {
            dispatch_async(dispatch_get_main_queue(), ^{ replyHandler(nil, @"Le moteur local n’est pas disponible."); });
            return;
        }
        PyGILState_STATE gil = PyGILState_Ensure();
        PyObject *result = PyObject_CallMethod(EngineInstance, "call", "s", request.UTF8String);
        NSString *json = result && PyUnicode_Check(result) ? [NSString stringWithUTF8String:PyUnicode_AsUTF8(result)] : nil;
        if (!result) PyErr_Print();
        Py_XDECREF(result);
        PyGILState_Release(gil);
        NSDictionary *response = json ? [NSJSONSerialization JSONObjectWithData:[json dataUsingEncoding:NSUTF8StringEncoding]
                                                                        options:0 error:nil] : nil;
        dispatch_async(dispatch_get_main_queue(), ^{
            replyHandler(response, response ? nil : @"L’opération n’a pas pu être enregistrée. Ta saisie est conservée.");
        });
    });
}
@end

// Appelé seulement par le bundle XCTest du pilote, avec données temporaires.
@interface RCPilotHarness : NSObject
+ (NSString *)runCheck;
@end
@implementation RCPilotHarness
+ (NSString *)runCheck {
    PrepareQueue();
    __block NSString *report = nil;
    dispatch_sync(EngineQueue, ^{
        if (!PrepareEngine()) return;
        PyGILState_STATE gil = PyGILState_Ensure();
        PyObject *module = PyImport_ImportModule("mobile.pilot_selftest");
        PyObject *result = module ? PyObject_CallMethod(module, "run", NULL) : NULL;
        if (result && PyUnicode_Check(result)) report = [NSString stringWithUTF8String:PyUnicode_AsUTF8(result)];
        if (!result) PyErr_Print();
        Py_XDECREF(result); Py_XDECREF(module);
        PyGILState_Release(gil);
    });
    return report;
}
@end

@implementation SceneDelegate
- (void)scene:(UIScene *)scene willConnectToSession:(UISceneSession *)session options:(UISceneConnectionOptions *)options {
    self.window = [[UIWindow alloc] initWithWindowScene:(UIWindowScene *)scene];
    self.window.overrideUserInterfaceStyle = UIUserInterfaceStyleDark;
    self.window.rootViewController = [[PilotViewController alloc] init];
    [self.window makeKeyAndVisible];
}
- (void)sceneWillResignActive:(UIScene *)scene {
    PilotViewController *controller = (PilotViewController *)self.window.rootViewController;
    [controller.speech interruptIfRunning];
}
- (void)sceneDidEnterBackground:(UIScene *)scene {
    PilotViewController *controller = (PilotViewController *)self.window.rootViewController;
    [controller.speech cancelAll];
    [controller.web evaluateJavaScript:@"window.pauseForInterruption?.()" completionHandler:nil];
}
@end

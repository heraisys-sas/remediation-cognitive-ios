#import <XCTest/XCTest.h>
#import <WebKit/WebKit.h>

@interface TestbedTests : XCTestCase
@end
@implementation TestbedTests
- (void)testWebViewCallsLocalEngine {
    UIWindowScene *scene = (UIWindowScene *)UIApplication.sharedApplication.connectedScenes.anyObject;
    UIViewController *controller = scene.windows.firstObject.rootViewController;
    WKWebView *web = [controller valueForKey:@"web"];
    XCTAssertNotNil(web);
    if (!web) return;
    NSPredicate *loaded = [NSPredicate predicateWithBlock:^BOOL(id object, NSDictionary *bindings) {
        return !web.loading && [web.URL.lastPathComponent isEqualToString:@"index.html"];
    }];
    XCTNSPredicateExpectation *page = [[XCTNSPredicateExpectation alloc] initWithPredicate:loaded object:web];
    [self waitForExpectations:@[page] timeout:20];
    XCTestExpectation *response = [self expectationWithDescription:@"Pont WebKit vers moteur local"];
    [web callAsyncJavaScript:@"for(let i=0;i<200&&document.getElementById('status').textContent;i++) await new Promise(r=>setTimeout(r,10)); await document.getElementById('start').onclick(); const r=await window.webkit.messageHandlers.runtime.postMessage({action:'view'}); window.pauseForInterruption(); const paused=document.getElementById('exercise').hidden; document.getElementById('resume').onclick(); return {result:r, title:document.querySelector('h1').textContent, error:document.getElementById('error').textContent, paused:paused, resumed:!document.getElementById('exercise').hidden};"
                   arguments:@{} inFrame:nil inContentWorld:WKContentWorld.pageWorld
           completionHandler:^(id value, NSError *error) {
        XCTAssertNil(error);
        XCTAssertTrue([value isKindOfClass:NSDictionary.class]);
        XCTAssertEqualObjects(value[@"title"], @"Calcul mental");
        XCTAssertEqualObjects(value[@"error"], @"");
        XCTAssertNotNil(value[@"result"][@"started"]);
        XCTAssertNotNil(value[@"result"][@"item"]);
        XCTAssertEqualObjects(value[@"paused"], @YES);
        XCTAssertEqualObjects(value[@"resumed"], @YES);
        [response fulfill];
    }];
    [self waitForExpectations:@[response] timeout:30];
}

- (void)testNativePythonPersistence {
    Class harness = NSClassFromString(@"RCPilotHarness");
    XCTAssertNotNil(harness);
    if (!harness) return;
    SEL selector = NSSelectorFromString(@"runCheck");
    NSString *(*run)(id, SEL) = (void *)[harness methodForSelector:selector];
    NSString *report = run(harness, selector);
    XCTAssertNotNil(report, @"Le service Python doit s'exécuter depuis l'app native");
    if (!report) return;
    NSDictionary *result = [NSJSONSerialization JSONObjectWithData:[report dataUsingEncoding:NSUTF8StringEncoding]
                                                           options:0 error:nil];
    XCTAssertEqualObjects(result[@"platform"], @"ios");
    XCTAssertEqualObjects(result[@"passed"], @5);
    NSLog(@"PILOT_RESULT=%@", report);
}
@end

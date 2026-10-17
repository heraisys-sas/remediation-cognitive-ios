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
    NSString *script = @"for(let i=0;i<200&&document.getElementById('status').textContent;i++) await new Promise(r=>setTimeout(r,10));"
        "await document.getElementById('start').onclick();"
        "const r=await window.webkit.messageHandlers.runtime.postMessage({action:'view'});"
        "window.pauseForInterruption(); const paused=document.getElementById('exercise').hidden;"
        "document.getElementById('resume').onclick();"
        "const resumed=!document.getElementById('exercise').hidden;"
        "for(let i=0;i<12;i++){const v=await request('view');"
        "await request('answer',{session_id:v.session_id,item_id:v.item.id,answer:'inconnu',elapsed_ms:1000});"
        "render(await request('view')); await document.getElementById('next').onclick();}"
        "const reprise=await request('view');"
        "const support=!document.getElementById('repriseSupport').hidden && document.getElementById('repriseSupport').textContent.includes(String(reprise.reprise_attendue));"
        "await document.getElementById('finish').onclick();"
        "document.getElementById('activity').value='acces-lexical';"
        "await document.getElementById('start').onclick();"
        "await document.getElementById('hint').onclick();"
        "const hinted=await request('view'); const hintVisible=Boolean(document.getElementById('hints').textContent);"
        "await document.getElementById('reveal').onclick(); const revealed=await request('view');"
        "await document.getElementById('finish').onclick();"
        "document.getElementById('activity').value='pqrst-guide'; await document.getElementById('start').onclick();"
        "await document.getElementById('protocol-continue').onclick();"
        "document.getElementById('protocol-option-1').onclick(); await document.getElementById('protocol-respond').onclick();"
        "await document.getElementById('protocol-continue').onclick();"
        "let field=document.getElementById('protocol-answer'); field.value='Que retenir ?'; field.oninput();"
        "await document.getElementById('protocol-respond').onclick(); await document.getElementById('protocol-continue').onclick();"
        "await document.getElementById('protocol-continue').onclick();"
        "const masked=!document.getElementById('protocol').textContent.includes('bureau de tabac de la place');"
        "field=document.getElementById('protocol-answer'); field.value='Le colis attend'; field.oninput();"
        "await document.getElementById('protocol-pause').onclick(); await document.getElementById('resume').onclick();"
        "const draft=document.getElementById('protocol-answer').value==='Le colis attend';"
        "await document.getElementById('protocol-reread').onclick(); await document.getElementById('protocol-continue').onclick();"
        "field=document.getElementById('protocol-answer'); field.value='Le colis attend au bureau de tabac avant jeudi avec une pièce d’identité avant la fermeture à 18 h'; field.oninput();"
        "await document.getElementById('protocol-respond').onclick(); await document.getElementById('protocol-continue').onclick();"
        "for(let i=0;i<2;i++){document.getElementById('protocol-option-0').onclick(); await document.getElementById('protocol-respond').onclick();}"
        "await document.getElementById('protocol-submit').onclick(); const pqrst=await request('view');"
        "return {result:r,title:document.querySelector('h1').textContent,error:document.getElementById('error').textContent,"
        "paused,resumed,support,lexical:hinted.activity==='acces-lexical' && hinted.hints_used===1 && hintVisible && revealed.feedback.assistee===true,"
        "pqrst:masked&&draft&&pqrst.feedback.sequence.observation.tentatives['4'][0].reponse==='Le colis attend'&&pqrst.feedback.sequence['1'].correcte===false&&document.getElementById('feedback').textContent.includes('sujet du texte : réponse à revoir')};";
    [web callAsyncJavaScript:script
                   arguments:@{} inFrame:nil inContentWorld:WKContentWorld.pageWorld
           completionHandler:^(id value, NSError *error) {
        XCTAssertNil(error);
        XCTAssertTrue([value isKindOfClass:NSDictionary.class]);
        XCTAssertEqualObjects(value[@"title"], @"PQRST guidé");
        XCTAssertEqualObjects(value[@"error"], @"");
        XCTAssertNotNil(value[@"result"][@"started"]);
        XCTAssertNotNil(value[@"result"][@"item"]);
        XCTAssertEqualObjects(value[@"paused"], @YES);
        XCTAssertEqualObjects(value[@"resumed"], @YES);
        XCTAssertEqualObjects(value[@"support"], @YES);
        XCTAssertEqualObjects(value[@"lexical"], @YES);
        XCTAssertEqualObjects(value[@"pqrst"], @YES);
        [response fulfill];
    }];
    [self waitForExpectations:@[response] timeout:60];
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
    XCTAssertEqualObjects(result[@"passed"], @9);
    NSLog(@"PILOT_RESULT=%@", report);
}
@end

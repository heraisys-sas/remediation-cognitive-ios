#import <XCTest/XCTest.h>
#import <WebKit/WebKit.h>

@interface TestbedTests : XCTestCase
@end
@interface UIViewController (PilotLocalURLChecks)
- (BOOL)isAllowedLocalURL:(NSURL *)url;
@end
@implementation TestbedTests
- (void)testLocalURLAliasesStayInsideResourceRoot {
    UIWindowScene *scene = (UIWindowScene *)UIApplication.sharedApplication.connectedScenes.anyObject;
    UIViewController *controller = scene.windows.firstObject.rootViewController;
    NSString *root = [controller valueForKey:@"allowedRoot"];
    NSURL *directory = [NSURL fileURLWithPath:root isDirectory:YES];
    NSURL *index = [directory URLByAppendingPathComponent:@"index.html"];
    XCTAssertTrue([controller isAllowedLocalURL:index]);
    XCTAssertFalse([controller isAllowedLocalURL:[NSURL URLWithString:@"https://example.com/index.html"]]);
    XCTAssertFalse([controller isAllowedLocalURL:[NSURL fileURLWithPath:[root stringByAppendingString:@"../outside.html"]]]);
    NSString *sibling = [[root stringByDeletingLastPathComponent] stringByAppendingString:@"-other/index.html"];
    XCTAssertFalse([controller isAllowedLocalURL:[NSURL fileURLWithPath:sibling]]);
    NSURL *temporary = [NSURL fileURLWithPath:[NSTemporaryDirectory() stringByAppendingPathComponent:NSUUID.UUID.UUIDString] isDirectory:YES];
    NSFileManager *files = NSFileManager.defaultManager;
    NSError *error = nil;
    XCTAssertTrue([files createDirectoryAtURL:temporary withIntermediateDirectories:YES attributes:nil error:&error]);
    @try {
        NSURL *alias = [temporary URLByAppendingPathComponent:@"alias" isDirectory:YES];
        XCTAssertTrue([files createSymbolicLinkAtURL:alias withDestinationURL:directory error:&error]);
        XCTAssertNil(error);
        XCTAssertTrue([controller isAllowedLocalURL:[alias URLByAppendingPathComponent:@"index.html"]]);
        NSURL *inside = [temporary URLByAppendingPathComponent:@"inside" isDirectory:YES];
        XCTAssertTrue([files createDirectoryAtURL:inside withIntermediateDirectories:YES attributes:nil error:&error]);
        NSURL *outside = [temporary URLByAppendingPathComponent:@"outside.html"];
        XCTAssertTrue([@"test" writeToURL:outside atomically:YES encoding:NSUTF8StringEncoding error:&error]);
        NSURL *escape = [inside URLByAppendingPathComponent:@"escape.html"];
        XCTAssertTrue([files createSymbolicLinkAtURL:escape withDestinationURL:outside error:&error]);
        UIViewController *isolated = [[controller class] new];
        NSString *canonical = [inside.URLByResolvingSymlinksInPath.URLByStandardizingPath.path stringByAppendingString:@"/"];
        [isolated setValue:canonical forKey:@"allowedRoot"];
        XCTAssertFalse([isolated isAllowedLocalURL:escape]);
    } @finally {
        [files removeItemAtURL:temporary error:nil];
    }
}

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
        "const pqrstOK=masked&&draft&&pqrst.feedback.sequence.observation.tentatives['4'][0].reponse==='Le colis attend'&&pqrst.feedback.sequence['1'].correcte===false&&document.getElementById('feedback').textContent.includes('sujet du texte : réponse à revoir');"
        "await document.getElementById('finish').onclick(); document.getElementById('activity').value='memoire-source'; await document.getElementById('start').onclick();"
        "const contextSession=await request('view'); let photoLoaded=false;"
        "for(let n=0;n<contextSession.total;n++){"
        "await document.getElementById('contextes-show').onclick();"
        "for(let k=0;k<750;k++){await new Promise(r=>setTimeout(r,20)); const v=await request('view'); const pic=document.querySelector('#contextes img'); if(v.contextes.phase==='exposition'&&!busy&&pic&&pic.complete&&pic.naturalWidth)break;}"
        "const im=document.querySelector('#contextes img'); photoLoaded=Boolean(im&&im.complete&&im.naturalWidth);"
        "if(!photoLoaded)throw Error('Photo locale non chargée');"
        "await contextesCommand('hide'); await document.getElementById('contextes-answer-0').onclick(); await document.getElementById('contextes-next').onclick();}"
        "const recall=await request('view'); const noPhoto=recall.contextes.pass==='rappel'&&!document.querySelector('#contextes img');"
        "await window.pauseForInterruption(); await document.getElementById('resume').onclick();"
        "const recallResumed=!document.querySelector('#contextes img')&&!document.getElementById('exercise').hidden;"
        "await document.getElementById('contextes-answer-0').onclick();"
        "const recalled=await request('view'); await document.getElementById('finish').onclick();"
        "return {contextes:photoLoaded&&noPhoto&&recallResumed&&recalled.contextes.phase==='feedback',result:r,title:document.querySelector('h1').textContent,error:document.getElementById('error').textContent,"
        "paused,resumed,support,lexical:hinted.activity==='acces-lexical' && hinted.hints_used===1 && hintVisible && revealed.feedback.assistee===true,"
        "pqrst:pqrstOK};";
    [web callAsyncJavaScript:script
                   arguments:@{} inFrame:nil inContentWorld:WKContentWorld.pageWorld
           completionHandler:^(id value, NSError *error) {
        XCTAssertNil(error);
        XCTAssertTrue([value isKindOfClass:NSDictionary.class]);
        XCTAssertEqualObjects(value[@"title"], @"Retrouver le contexte");
        XCTAssertEqualObjects(value[@"error"], @"");
        XCTAssertNotNil(value[@"result"][@"started"]);
        XCTAssertNotNil(value[@"result"][@"item"]);
        XCTAssertEqualObjects(value[@"paused"], @YES);
        XCTAssertEqualObjects(value[@"resumed"], @YES);
        XCTAssertEqualObjects(value[@"support"], @YES);
        XCTAssertEqualObjects(value[@"lexical"], @YES);
        XCTAssertEqualObjects(value[@"pqrst"], @YES);
        XCTAssertEqualObjects(value[@"contextes"], @YES);
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
    XCTAssertEqualObjects(result[@"passed"], @11);
    NSLog(@"PILOT_RESULT=%@", report);
}
@end

#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN
@interface RCSpeechController : NSObject
@property(nonatomic, copy, nullable) void (^eventSink)(NSDictionary *event);
- (void)handle:(NSDictionary *)command reply:(void (^)(id _Nullable, NSString * _Nullable))reply;
- (void)cancelAll;
- (void)interruptIfRunning;
@end
NS_ASSUME_NONNULL_END

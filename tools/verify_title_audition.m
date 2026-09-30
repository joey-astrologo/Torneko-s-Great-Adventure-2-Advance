#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>
@interface AuditDelegate : NSObject <WKNavigationDelegate>
@property WKWebView *view;
@property NSString *script;
@property NSString *output;
@property NSInteger attempts;
@end
@implementation AuditDelegate
- (void)webView:(WKWebView *)view didFinishNavigation:(WKNavigation *)navigation {
 [self runWhenReady];
}
- (void)runWhenReady {
 [self.view evaluateJavaScript:@"(()=>{if(window.TITLE_AUDITION&&window.TITLE_AUDITION.ready&&!window.__titleStarted){window.__titleStarted=true;window.TITLE_AUDITION.verify().then(r=>{window.__titleResult=r;},e=>{window.__titleResult={status:'failed',error:e.message};});}return JSON.stringify({ready:!!window.__titleResult,error:(window.__titleResult&&window.__titleResult.status==='failed'?window.__titleResult.error:document.getElementById('error').textContent)||null});})()" completionHandler:^(id result,NSError *error){
  if(error){fprintf(stderr,"Readiness error: %s\n",error.description.UTF8String);exit(1);}
  NSDictionary *state=[NSJSONSerialization JSONObjectWithData:[result dataUsingEncoding:NSUTF8StringEncoding] options:0 error:nil];
  if(state[@"error"]!=[NSNull null]){fprintf(stderr,"Studio error: %s\n",[state[@"error"] UTF8String]);exit(1);}
  if([state[@"ready"] boolValue]){[self runChecks];return;}
  if(++self.attempts>1200){fprintf(stderr,"Studio readiness timed out\n");exit(1);}
  dispatch_after(dispatch_time(DISPATCH_TIME_NOW,100*NSEC_PER_MSEC),dispatch_get_main_queue(),^{[self runWhenReady];});
 }];
}
- (void)runChecks {
 WKWebView *view=self.view;
 [view evaluateJavaScript:self.script completionHandler:^(id result,NSError *error){
  if(error){fprintf(stderr,"%s\n",error.description.UTF8String);exit(1);}
  NSData *json=[NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted error:nil];
  [json writeToFile:[self.output stringByAppendingPathComponent:@"browser-checks.json"] atomically:YES];
  WKSnapshotConfiguration *config=[WKSnapshotConfiguration new];config.rect=CGRectMake(0,0,1280,1050);
  [view takeSnapshotWithConfiguration:config completionHandler:^(NSImage *image,NSError *captureError){
   if(captureError || !image){fprintf(stderr,"WebKit screenshot failed: %s\n",captureError.description.UTF8String);exit(1);}
   if(image){NSBitmapImageRep *bitmap=[[NSBitmapImageRep alloc] initWithData:image.TIFFRepresentation];NSData *png=[bitmap representationUsingType:NSBitmapImageFileTypePNG properties:@{}];[png writeToFile:[self.output stringByAppendingPathComponent:@"audition-browser.png"] atomically:YES];}
   [view evaluateJavaScript:@"document.getElementById('backgrounds').scrollIntoView(); null" completionHandler:^(id ignored,NSError *scrollError){
    if(scrollError){fprintf(stderr,"Background scroll failed\n");exit(1);}
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW,200*NSEC_PER_MSEC),dispatch_get_main_queue(),^{
     [view takeSnapshotWithConfiguration:config completionHandler:^(NSImage *background,NSError *backgroundError){
      if(backgroundError||!background){fprintf(stderr,"Background screenshot failed\n");exit(1);}
      NSBitmapImageRep *bitmap=[[NSBitmapImageRep alloc] initWithData:background.TIFFRepresentation];
      NSData *png=[bitmap representationUsingType:NSBitmapImageFileTypePNG properties:@{}];
      [png writeToFile:[self.output stringByAppendingPathComponent:@"background-browser.png"] atomically:YES];
      fprintf(stdout,"Title and background browser checks completed.\n");exit(0);
     }];
    });
   }];
  }];
 }];
}
- (void)webView:(WKWebView *)view didFailProvisionalNavigation:(WKNavigation *)navigation withError:(NSError *)error {fprintf(stderr,"%s\n",error.description.UTF8String);exit(1);}
@end
int main(int argc,const char **argv){@autoreleasepool{
 if(argc!=4){fprintf(stderr,"Usage: check page.html checks.js output-directory\n");return 1;}
 [NSApplication sharedApplication];
 NSString *path=[NSString stringWithUTF8String:argv[1]],*scriptPath=[NSString stringWithUTF8String:argv[2]],*output=[NSString stringWithUTF8String:argv[3]];
 NSWindow *window=[[NSWindow alloc] initWithContentRect:NSMakeRect(0,0,1280,1050) styleMask:NSWindowStyleMaskBorderless backing:NSBackingStoreBuffered defer:NO];
 AuditDelegate *delegate=[AuditDelegate new];delegate.script=[NSString stringWithContentsOfFile:scriptPath encoding:NSUTF8StringEncoding error:nil];delegate.output=output;
 WKWebViewConfiguration *configuration=[WKWebViewConfiguration new];configuration.websiteDataStore=[WKWebsiteDataStore nonPersistentDataStore];delegate.view=[[WKWebView alloc] initWithFrame:NSMakeRect(0,0,1280,1050) configuration:configuration];delegate.view.navigationDelegate=delegate;window.contentView=delegate.view;
 NSURL *url=[NSURL fileURLWithPath:path];[delegate.view loadFileURL:url allowingReadAccessToURL:[[[url URLByDeletingLastPathComponent] URLByDeletingLastPathComponent] URLByDeletingLastPathComponent]];
 [NSTimer scheduledTimerWithTimeInterval:120 repeats:NO block:^(NSTimer *timer){fprintf(stderr,"WebKit timeout\n");exit(2);}];
 [NSApp run];
}}

#import <Cocoa/Cocoa.h>
#import <WebKit/WebKit.h>
@interface AuditDelegate : NSObject <WKNavigationDelegate>
@property WKWebView *view;
@property NSString *script;
@property NSString *output;
@end
@implementation AuditDelegate
- (void)webView:(WKWebView *)view didFinishNavigation:(WKNavigation *)navigation {
 [view evaluateJavaScript:self.script completionHandler:^(id result,NSError *error){
  if(error){fprintf(stderr,"%s\n",error.description.UTF8String);exit(1);}
  NSData *json=[NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted error:nil];
  [json writeToFile:[self.output stringByAppendingPathComponent:@"browser-checks.json"] atomically:YES];
  WKSnapshotConfiguration *config=[WKSnapshotConfiguration new];config.rect=CGRectMake(0,0,1280,1050);
  [view takeSnapshotWithConfiguration:config completionHandler:^(NSImage *image,NSError *captureError){
   if(captureError || !image){fprintf(stderr,"WebKit screenshot failed: %s\n",captureError.description.UTF8String);exit(1);}
   if(image){NSBitmapImageRep *bitmap=[[NSBitmapImageRep alloc] initWithData:image.TIFFRepresentation];NSData *png=[bitmap representationUsingType:NSBitmapImageFileTypePNG properties:@{}];[png writeToFile:[self.output stringByAppendingPathComponent:@"audition-browser.png"] atomically:YES];}
   fprintf(stdout,"%s\n",[[NSString alloc] initWithData:json encoding:NSUTF8StringEncoding].UTF8String);exit(0);
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
 [NSTimer scheduledTimerWithTimeInterval:45 repeats:NO block:^(NSTimer *timer){fprintf(stderr,"WebKit timeout\n");exit(2);}];
 [NSApp run];
}}

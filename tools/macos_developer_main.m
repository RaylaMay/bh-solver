/* Local macOS developer entry point; not a standalone distribution runtime.
 *
 * Keep the application's Mach-O executable alive while hosting CPython in this
 * process. The former shell/exec entry failed to read the venv in Documents,
 * consistent with macOS folder-permission attribution loss before Qt could load.
 * Paths are supplied by the generated bundle; nothing is downloaded or granted.
 * CPython and Qt remain dynamic, unmodified libraries in the existing checkout.
 */
#import <AppKit/AppKit.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (*PythonBytesMain)(int, char **);

static int startupFailure(NSString *message) {
    fprintf(stderr, "BH_DESKTOP_STARTUP_FAILED: %s\n", message.UTF8String);
    [NSApplication sharedApplication];
    NSAlert *alert = [[NSAlert alloc] init];
    alert.messageText = @"BH solver could not start";
    alert.informativeText = message;
    [alert addButtonWithTitle:@"Close"];
    [alert runModal];
    return EXIT_FAILURE;
}

int main(int argc, char **argv) {
    @autoreleasepool {
        NSDictionary *info = NSBundle.mainBundle.infoDictionary;
        NSString *python = info[@"BHDevelopmentPythonExecutable"];
        NSString *library = info[@"BHDevelopmentPythonLibrary"];
        NSString *dataRoot = info[@"BHDevelopmentDataRoot"];
        if (![python isKindOfClass:NSString.class] || !python.isAbsolutePath ||
            ![library isKindOfClass:NSString.class] || !library.isAbsolutePath ||
            ![dataRoot isKindOfClass:NSString.class] || !dataRoot.isAbsolutePath) {
            return startupFailure(@"The development launcher configuration is invalid. "
                                  @"Rebuild it from this project's launcher helper.");
        }
        // Extension modules resolve Python symbols from the shared interpreter.
        void *runtime = dlopen(library.fileSystemRepresentation, RTLD_NOW | RTLD_GLOBAL);
        PythonBytesMain runPython = runtime ? (PythonBytesMain)dlsym(runtime, "Py_BytesMain") : NULL;
        if (!runPython) {
            return startupFailure(@"The configured Python runtime is unavailable. "
                                  @"Restore the project environment and rebuild the launcher.");
        }
        char **arguments = calloc((size_t)argc + 5, sizeof(char *));
        if (!arguments) {
            return startupFailure(@"There is not enough memory to start the application.");
        }
        // argv[0] selects this checkout's venv, retaining its installed packages.
        arguments[0] = (char *)python.fileSystemRepresentation;
        arguments[1] = "-m";
        arguments[2] = "bh_sim.desktop_launcher";
        arguments[3] = "--data-root";
        arguments[4] = (char *)dataRoot.fileSystemRepresentation;
        for (int index = 1; index < argc; ++index) {
            arguments[index + 4] = argv[index];
        }
        int result = runPython(argc + 4, arguments);
        free(arguments);
        // Keep the library loaded through process teardown: extension destructors
        // may still reference Python symbols after Py_BytesMain returns.
        return result;
    }
}

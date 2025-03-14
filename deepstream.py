import sys
import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstNvInfer", "1.0")
gi.require_version("GstNvTracker", "1.0")
from gi.repository import Gst, GLib

# Initialize GStreamer
Gst.init(None)

def create_pipeline(input_file, output_file):
    pipeline = Gst.parse_launch(
        f"filesrc location={input_file} ! qtdemux ! h264parse ! nvv4l2decoder ! "
        f"nvvideoconvert ! nvstreammux name=mux batch-size=1 width=1280 height=720 ! "
        f"nvinfer config-file-path=dstest1_pgie_config.txt ! "
        f"nvtracker ! nvvideoconvert ! nvv4l2h264enc ! h264parse ! "
        f"mp4mux ! filesink location={output_file}"
    )
    
    return pipeline

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 deepstream_app.py <input.mp4> <output.mp4>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    pipeline = create_pipeline(input_file, output_file)
    if not pipeline:
        print("Error: Unable to create pipeline")
        sys.exit(1)

    loop = GLib.MainLoop()

    def bus_call(bus, message, loop):
        t = message.type
        if t == Gst.MessageType.EOS:
            print("End of stream")
            loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Error: {err}, {debug}")
            loop.quit()
        return True

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)

    print("Starting DeepStream pipeline...")
    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop.run()
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        pipeline.set_state(Gst.State.NULL)

if __name__ == "__main__":
    main()

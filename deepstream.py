import sys
sys.path.append('../')
import os
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst
from common.platform_info import PlatformInfo
from common.bus_call import bus_call

import pyds

PGIE_CLASS_ID_VEHICLE = 0
PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 2
PGIE_CLASS_ID_ROADSIGN = 3
MUXER_BATCH_TIMEOUT_USEC = 33000

def osd_sink_pad_buffer_probe(pad,info,u_data):
    frame_number=0
    num_rects=0

    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer ")
        return
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        obj_counter = {
            PGIE_CLASS_ID_VEHICLE:0,
            PGIE_CLASS_ID_PERSON:0,
            PGIE_CLASS_ID_BICYCLE:0,
            PGIE_CLASS_ID_ROADSIGN:0
        }
        frame_number=frame_meta.frame_num
        num_rects = frame_meta.num_obj_meta
        l_obj=frame_meta.obj_meta_list
        while l_obj is not None:
            try:
                obj_meta=pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break
            obj_counter[obj_meta.class_id] += 1
            obj_meta.rect_params.border_color.set(0.0, 0.0, 1.0, 0.8) 
            try: 
                l_obj=l_obj.next
            except StopIteration:
                break

        display_meta=pyds.nvds_acquire_display_meta_from_pool(batch_meta)
        display_meta.num_labels = 1
        py_nvosd_text_params = display_meta.text_params[0]
        py_nvosd_text_params.display_text = "Frame Number={} Number of Objects={} Vehicle_count={} Person_count={}".format(
            frame_number, num_rects, obj_counter[PGIE_CLASS_ID_VEHICLE], obj_counter[PGIE_CLASS_ID_PERSON]
        )
        py_nvosd_text_params.x_offset = 10
        py_nvosd_text_params.y_offset = 12
        py_nvosd_text_params.font_params.font_name = "Serif"
        py_nvosd_text_params.font_params.font_size = 10
        py_nvosd_text_params.font_params.font_color.set(1.0, 1.0, 1.0, 1.0)
        py_nvosd_text_params.set_bg_clr = 1
        py_nvosd_text_params.text_bg_clr.set(0.0, 0.0, 0.0, 1.0)
        
        print(pyds.get_string(py_nvosd_text_params.display_text))
        pyds.nvds_add_display_meta_to_frame(frame_meta, display_meta)
        
        try:
            l_frame=l_frame.next
        except StopIteration:
            break
			
    return Gst.PadProbeReturn.OK	

def decodebin_pad_added(decodebin, pad, streammux):
    print("Inside decodebin_pad_added")
    caps = pad.query_caps(None)
    caps_str = caps.to_string() if caps else "Unknown"
    print(f"Pad caps: {caps_str}")

    if caps and caps_str.startswith("video/x-raw"):
        sinkpad = streammux.get_request_pad("sink_0")
        if not sinkpad:
            sys.stderr.write("Error: Unable to get sink pad from streammux\n")
            return

        if pad.link(sinkpad) != Gst.PadLinkReturn.OK:
            sys.stderr.write("Error: Failed to link decodebin pad to streammux\n")


def main(args):
    if len(args) != 2:
        sys.stderr.write("Usage: %s <media file>\n" % args[0])
        sys.exit(1)

    Gst.init(None)

    print("Creating Pipeline\n")
    pipeline = Gst.Pipeline()

    if not pipeline:
        sys.stderr.write("Failed to create Pipeline\n")
        return

    source = Gst.ElementFactory.make("filesrc", "file-source")
    decodebin = Gst.ElementFactory.make("decodebin", "decoder")
    streammux = Gst.ElementFactory.make("nvstreammux", "stream-muxer")
    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    nvtracker = Gst.ElementFactory.make("nvtracker", "tracker")
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "converter")
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
    encoder = Gst.ElementFactory.make("nvv4l2h264enc", "h264-encoder")
    parser = Gst.ElementFactory.make("h264parse", "h264-parser")
    muxer = Gst.ElementFactory.make("qtmux", "muxer")
    sink = Gst.ElementFactory.make("filesink", "file-output")

    if not all([source, decodebin, streammux, pgie, nvtracker, nvvidconv, nvosd, encoder, parser, muxer, sink]):
        sys.stderr.write("Failed to create one or more elements\n")
        return

    source.set_property("location", args[1])
    streammux.set_property("batch-size", 1)
    streammux.set_property("width", 1920)
    streammux.set_property("height", 1080)
    streammux.set_property("batched-push-timeout", MUXER_BATCH_TIMEOUT_USEC)
    pgie.set_property("config-file-path", "dstest1_pgie_config.txt")

    # Tracker configuration
    nvtracker.set_property("tracker-width", 960)
    nvtracker.set_property("tracker-height", 544)
    nvtracker.set_property("ll-lib-file", "/opt/nvidia/deepstream/deepstream/lib/libnvds_nvmultiobjecttracker.so")
    nvtracker.set_property("ll-config-file", "/opt/nvidia/deepstream/deepstream-7.1/samples/configs/deepstream-app/config_tracker_NvDeepSORT.yml")
    nvtracker.set_property("gpu_id", 0)

    sink.set_property("location", "iou_tracker_test_1.mp4")
    sink.set_property("sync", False)

    pipeline.add(source)
    pipeline.add(decodebin)
    pipeline.add(streammux)
    pipeline.add(pgie)
    pipeline.add(nvtracker)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(encoder)
    pipeline.add(parser)
    pipeline.add(muxer)
    pipeline.add(sink)

    # Link static elements
    streammux.link(pgie)
    pgie.link(nvtracker)  # Linked Tracker after PGIE
    nvtracker.link(nvvidconv)
    nvvidconv.link(nvosd)
    nvosd.link(encoder)
    encoder.link(parser)
    parser.link(muxer)
    muxer.link(sink)

    decodebin.connect("pad-added", decodebin_pad_added, streammux)

    # Add message bus handling
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    loop = GLib.MainLoop()
    bus.connect("message", bus_call, loop)

    print("Starting pipeline, saving output to iou_tracker_test_1.mp4\n")
    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop.run()
    except KeyboardInterrupt:
        pass

    print("Stopping pipeline\n")
    pipeline.set_state(Gst.State.NULL)

if __name__ == '__main__':
    sys.exit(main(sys.argv))

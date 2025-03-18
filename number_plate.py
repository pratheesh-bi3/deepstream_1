import sys
import gi
import pyds

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GLib

def osd_sink_pad_buffer_probe(pad, info, u_data):
    frame_meta_list = []
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer")
        return Gst.PadProbeReturn.OK
    
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    for frame_meta in pyds.NvDsFrameMeta.cast(batch_meta.frame_meta_list):
        for obj_meta in pyds.NvDsObjectMeta.cast(frame_meta.obj_meta_list):
            if obj_meta.class_id == 1:  # Assuming class_id 1 is number plates
                print(f"Detected Number Plate at ({obj_meta.rect_params.left}, {obj_meta.rect_params.top})")
    
    return Gst.PadProbeReturn.OK

def main():
    Gst.init(None)
    pipeline = Gst.parse_launch(
        "filesrc location=sample_720p.mp4 ! decodebin ! videoconvert ! nvvideoconvert ! "
        "nvinfer config-file-path=number_plate_detector_config.txt ! nvvideoconvert ! "
        "nvv4l2h264enc bitrate=8000000 ! h264parse ! mp4mux ! filesink location=number_plate_1.mp4")
    
    pipeline.set_state(Gst.State.PLAYING)
    bus = pipeline.get_bus()
    while True:
        msg = bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS | Gst.MessageType.ERROR)
        if msg:
            break
    
    pipeline.set_state(Gst.State.NULL)
    print("Pipeline stopped")
    
if __name__ == '__main__':
    sys.exit(main())

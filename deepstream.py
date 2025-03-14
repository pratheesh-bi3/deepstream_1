import sys
import gi
import cv2
import numpy as np
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import pyds

PGIE_CLASS_ID_VEHICLE = 0
PGIE_CLASS_ID_PERSON = 1

def process_frame(gst_buffer):
    """Extracts frames from GstBuffer and processes them using OpenCV."""
    n_frame = pyds.get_nvds_buf_surface(hash(gst_buffer), 0)  # Get frame as numpy array
    frame = np.array(n_frame, copy=True, order='C')  # Convert to OpenCV format (BGR)

    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list

    while l_frame is not None:
        frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        l_obj = frame_meta.obj_meta_list

        while l_obj is not None:
            obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)

            # Extract bounding box coordinates
            x1, y1 = int(obj_meta.rect_params.left), int(obj_meta.rect_params.top)
            x2, y2 = int(x1 + obj_meta.rect_params.width), int(y1 + obj_meta.rect_params.height)

            # Draw bounding box using OpenCV
            color = (255, 0, 0)  # Blue
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            try:
                l_obj = l_obj.next
            except StopIteration:
                break

        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    return frame  # Return the processed frame

def osd_sink_pad_buffer_probe(pad, info, u_data):
    """Extracts frames and applies OpenCV processing."""
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer")
        return Gst.PadProbeReturn.OK

    frame = process_frame(gst_buffer)

    # Save frame to MP4 using OpenCV
    writer.write(frame)

    return Gst.PadProbeReturn.OK

# Set up OpenCV video writer
output_file = "output.mp4"
frame_width, frame_height, fps = 1280, 720, 30
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter(output_file, fourcc, fps, (frame_width, frame_height))

def main():
    Gst.init(None)

    pipeline = Gst.parse_launch(
    "filesrc location=sample_720p.mp4 ! qtdemux ! h264parse ! nvv4l2decoder ! "
    "nvvideoconvert ! video/x-raw(memory:NVMM), format=NV12 ! "
    "nvinfer config-file-path=dstest1_pgie_config.txt ! "
    "nvvideoconvert ! nvv4l2h264enc ! h264parse ! qtmux ! filesink location=output.mp4")

    sink = pipeline.get_by_name("filesink0")
    sink_pad = sink.get_static_pad("sink")
    sink_pad.add_probe(Gst.PadProbeType.BUFFER, osd_sink_pad_buffer_probe, 0)

    loop = GLib.MainLoop()
    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop.run()
    except:
        pass

    pipeline.set_state(Gst.State.NULL)
    writer.release()  # Release OpenCV writer

if __name__ == "__main__":
    sys.exit(main())

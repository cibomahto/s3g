import unittest
import sys
import io
import s3g

class CRCTests(unittest.TestCase):
  def test_cases(self):
    # Calculated using the processing tool 'ibutton_crc'
    cases = [
      [b'', 0],
      [b'abcdefghijk', 0xb4],
      [b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f', 0x3c],
    ]
    for case in cases:
      assert s3g.CalculateCRC(case[0]) == case[1]


class EncodeTests(unittest.TestCase):
  def test_encode_int32(self):
    cases = [
      [0,            '\x00\x00\x00\x00'],
      [-2147483648,  '\x00\x00\x00\x80'],
      [2147483647,   '\xFF\xFF\xFF\x7F'],
    ]
    for case in cases:
      assert s3g.EncodeInt32(case[0]) == case[1]
    
  def test_encode_uint32(self):
    cases = [
      [0,            '\x00\x00\x00\x00'],
      [2147483647,   '\xFF\xFF\xFF\x7F'],
      [4294967295,   '\xFF\xFF\xFF\xFF'],
    ]
    for case in cases:
      assert s3g.EncodeUint32(case[0]) == case[1]


class PacketEncodeTests(unittest.TestCase):
  def test_reject_oversize_payload(self):
    payload = bytearray()
    for i in range (0, s3g.maximum_payload_length + 1):
      payload.append(i)
    self.assertRaises(s3g.PacketLengthError,s3g.EncodePayload,payload)

  def test_packet_length(self):
    payload = 'abcd'
    packet = s3g.EncodePayload(payload)
    assert len(packet) == len(payload) + 3

  def test_packet_header(self):
    payload = 'abcd'
    packet = s3g.EncodePayload(payload)

    assert packet[0] == s3g.header

  def test_packet_length_field(self):
    payload = 'abcd'
    packet = s3g.EncodePayload(payload)
    assert packet[1] == len(payload)

  def test_packet_crc(self):
    payload = 'abcd'
    packet = s3g.EncodePayload(payload)
    assert packet[6] == s3g.CalculateCRC(payload);


class PacketDecodeTests(unittest.TestCase):
  def test_undersize_packet(self):
    packet = bytearray('abc')
    self.assertRaises(s3g.PacketLengthError,s3g.DecodePacket,packet)
    
  def test_wrong_header(self):
    packet = bytearray('abcd')
    self.assertRaises(s3g.PacketHeaderError,s3g.DecodePacket,packet)

  def test_bad_packet_length_field(self):
    packet = bytearray()
    packet.append(s3g.header)
    packet.append(5)
    packet.extend('ab')
    self.assertRaises(s3g.PacketLengthFieldError,s3g.DecodePacket,packet)

  def test_bad_crc(self):
    packet = bytearray()
    packet.append(s3g.header)
    packet.append(1)
    packet.extend('a')
    packet.append(s3g.CalculateCRC('a')+1)
    self.assertRaises(s3g.PacketCRCError,s3g.DecodePacket,packet)

  def test_got_payload(self):
    expected_payload = bytearray('abcde')

    packet = bytearray()
    packet.append(s3g.header)
    packet.append(len(expected_payload))
    packet.extend(expected_payload)
    packet.append(s3g.CalculateCRC(expected_payload))

    payload = s3g.DecodePacket(packet)
    assert payload == expected_payload


class PacketStreamDecoderTests(unittest.TestCase):
  def setUp(self):
    self.s = s3g.PacketStreamDecoder()

  def tearDown(self):
    self.s = None

  def test_starts_in_wait_for_header_mode(self):
    assert(self.s.state == 'WAIT_FOR_HEADER')
    assert(len(self.s.payload) == 0)
    assert(self.s.expected_length == 0)

  def test_reject_bad_header(self):
    self.assertRaises(s3g.PacketHeaderError,self.s.ParseByte,0x00)
    assert(self.s.state == 'WAIT_FOR_HEADER')

  def test_accept_header(self):
    self.s.ParseByte(s3g.header)
    assert(self.s.state == 'WAIT_FOR_LENGTH')

  def test_reject_bad_size(self):
    self.s.ParseByte(s3g.header)
    self.assertRaises(s3g.PacketLengthFieldError,self.s.ParseByte,s3g.maximum_payload_length+1)

  def test_accept_size(self):
    self.s.ParseByte(s3g.header)
    self.s.ParseByte(s3g.maximum_payload_length)
    assert(self.s.state == 'WAIT_FOR_DATA')
    assert(self.s.expected_length == s3g.maximum_payload_length)

  def test_accepts_data(self):
    self.s.ParseByte(s3g.header)
    self.s.ParseByte(s3g.maximum_payload_length)
    for i in range (0, s3g.maximum_payload_length):
      self.s.ParseByte(i)

    assert(self.s.expected_length == s3g.maximum_payload_length)
    for i in range (0, s3g.maximum_payload_length):
      assert(self.s.payload[i] == i)

  def test_reject_bad_crc(self):
    payload = 'abcde'
    self.s.ParseByte(s3g.header)
    self.s.ParseByte(len(payload))
    for i in range (0, len(payload)):
      self.s.ParseByte(payload[i])
    self.assertRaises(s3g.PacketCRCError,self.s.ParseByte,s3g.CalculateCRC(payload)+1)

  def test_accepts_crc(self):
    payload = 'abcde'
    self.s.ParseByte(s3g.header)
    self.s.ParseByte(len(payload))
    for i in range (0, len(payload)):
      self.s.ParseByte(payload[i])
    self.s.ParseByte(s3g.CalculateCRC(payload))
    assert(self.s.state == 'PAYLOAD_READY')
    assert(self.s.payload == payload)


class ReplicatorTests(unittest.TestCase):
  """
  Emulate a machine
  """
  def setUp(self):
    self.r = s3g.Replicator()
    self.outputstream = io.BytesIO() # Stream that we will send responses on
    self.inputstream = io.BytesIO()  # Stream that we will receive commands on
    self.file = io.BufferedRWPair(self.outputstream, self.inputstream)
    self.r.file = self.file

  def tearDown(self):
    self.r = None
    self.outputstream = None
    self.inputstream = None
    self.file = None

  def test_send_command_timeout(self):
    """
    Time out when no data is received. The input stream should have max_rety_count copies of the
    payload packet in it.
    """
    payload = 'abcde'
    expected_packet = s3g.EncodePayload(payload)

    self.assertRaises(s3g.TransmissionError,self.r.SendCommand,payload)

    #TODO: We should use a queue here, it doesn't make sense to shove this in a file buffer?
    self.inputstream.seek(0)

    for i in range (0, s3g.max_retry_count):
      for byte in expected_packet:
        assert byte == ord(self.inputstream.read(1))

  def test_send_command_many_bad_responses(self):
    """
    Passing case: test that the transmission can recover from one less than the alloted
    number of errors.
    """
    payload = 'abcde'
    expected_packet = s3g.EncodePayload(payload)

    expected_response_payload = '12345'
    for i in range (0, s3g.max_retry_count - 1):
      self.outputstream.write('a')
    self.outputstream.write(s3g.EncodePayload(expected_response_payload))

    #TODO: We should use a queue here, it doesn't make sense to shove this in a file buffer?
    self.outputstream.seek(0)

    assert (expected_response_payload == self.r.SendCommand(payload))
    #TODO: We should use a queue here, it doesn't make sense to shove this in a file buffer?
    self.inputstream.seek(0)
    for i in range (0, s3g.max_retry_count - 1):
      for byte in expected_packet:
        assert byte == ord(self.inputstream.read(1))

  def test_send_command(self):
    """
    Passing case: Preload the buffer with a correctly formatted expected response, and
    verify that it works correctly.
    """
    payload = 'abcde'

    expected_response_payload = '12345'
    self.outputstream.write(s3g.EncodePayload(expected_response_payload))
    #TODO: We should use a queue here, it doesn't make sense to shove this in a file buffer?
    self.outputstream.seek(0)

    assert (expected_response_payload == self.r.SendCommand(payload))
    assert (s3g.EncodePayload(payload) == self.inputstream.getvalue())

  # TODO: Test timing based errors- can we send half a response, get it to re-send, then send a regular response?

  def test_queue_extended_point(self):
    expected_target = [1,2,3,4,5]
    expected_velocity = 6
    self.r.Move(expected_target, expected_velocity)

    packet = bytearray(self.inputstream.getvalue())

    payload = s3g.DecodePacket(packet)
    assert payload[0] == s3g.command_map['QUEUE_EXTENDED_POINT']
    for i in range(0, 5):
      assert s3g.EncodeInt32(expected_target[i]) == payload[(i*4+1):(i*4+5)]


if __name__ == "__main__":
  unittest.main()

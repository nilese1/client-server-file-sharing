import ntplib

class Metrics:
    def __init__(self, client_ip):
        self.ntpClient = ntplib.NTPClient()
        self.client_ip = client_ip

    # put data somewhere. maybe dataframe or dictionary
    def calculateMetrics(self, type, ntpStart, ntpEnd, bytes_transferred):
        if ntpStart == -1 or ntpEnd == -1:
            print(f"Invalid times detected. Stop calculation")
            return
        
        elapsedTime = ntpEnd - ntpStart
        transferRate = (bytes_transferred / 1024) / elapsedTime #kbps
        print(f'TOTAL TIME TAKEN for {type} {bytes_transferred} bytes: {elapsedTime}... {transferRate}kbps')

    def getNTPTime(self):
        try:
            ntp_res = self.ntpClient.request("0.pool.ntp.org", version=3)
            return ntp_res.tx_time
        except Exception as e:
            print(f"Error getting NTP time, returning local time")
            return -1


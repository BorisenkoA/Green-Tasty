using Amazon.Lambda.Core;
using Amazon.S3;
using Amazon.S3.Model;
using APIHandler.Constants;
using System;
using System.Buffers.Binary;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Threading.Tasks;

namespace APIHandler.Services;

public class S3ImageService
{
    private readonly IAmazonS3 _s3Client;

    public S3ImageService(IAmazonS3 s3Client)
    {
        _s3Client = s3Client;
    }

    public async Task<string> UploadImageAsync(byte[] imageBytes, string bucketName, string fileName, ILambdaLogger logger,
        string? folder = null)
    {
        using var stream = new MemoryStream(imageBytes);
        string contentType = GetImageContentType(imageBytes);
        var key = string.IsNullOrWhiteSpace(folder)
            ? $"{fileName}"
            : $"{folder}/{fileName}";

        var request = new PutObjectRequest
        {
            BucketName = bucketName,
            Key = key,
            InputStream = stream,
            ContentType = contentType
        };

        await _s3Client.PutObjectAsync(request);

        return request.Key;
    }

    public string GetPublicUrl(string bucketName, string imageKey)
    {
        return $"https://{bucketName}.s3.{ResourceNames.Region}.amazonaws.com/{imageKey}";
    }

    public string GetImageUrl(string bucketName, string imageKey)
    {
        var request = new GetPreSignedUrlRequest
        {
            BucketName = bucketName,
            Key = imageKey,
            Expires = DateTime.UtcNow.AddMinutes(10)
        };
        return _s3Client.GetPreSignedURL(request);
    }

    public string GetPreSignedImageUrl(string bucketName, string imageKey)
    {
        var request = new GetPreSignedUrlRequest
        {
            BucketName = bucketName,
            Key = imageKey,
            Expires = DateTime.UtcNow.AddHours(1),
        };
        return _s3Client.GetPreSignedURL(request);
    }

    public static byte[] GetImageBytesFromBase64(string base64String)
    {
        int commaIndex = base64String.IndexOf(',');
        if (commaIndex != -1)
        {
            base64String = base64String.Substring(commaIndex + 1);
        }

        return Convert.FromBase64String(base64String);
    }

    public async Task<string> GetImageKey(string imageBase64, string bucketName, string folderName, string fileName, ILambdaLogger logger)
    {
        var imageBytes = GetImageBytesFromBase64(imageBase64);

        var imageKey =
            await UploadImageAsync(imageBytes, bucketName, fileName, logger, folderName);
        return imageKey;
    }

    public async Task<byte[]> DownloadImageAsync(string bucketName, string key)
    {
        var response = await _s3Client.GetObjectAsync(bucketName, key);
        using var ms = new MemoryStream();
        await response.ResponseStream.CopyToAsync(ms);
        return ms.ToArray();
    }

    public async Task DeleteImageAsync(string bucketName, string key)
    {
        await _s3Client.DeleteObjectAsync(bucketName, key);
    }

    public static bool CompareImagesHash(byte[] a, byte[] b)
    {
        using var sha = SHA256.Create();
        return sha.ComputeHash(a).SequenceEqual(sha.ComputeHash(b));
    }

    private static string GetImageContentType(byte[] imgData)
    {
        ReadOnlySpan<byte> data = imgData;

        if (data.Length >= 24
            && data[..8].SequenceEqual(new byte[] { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A })
            && data.Slice(12, 4).SequenceEqual("IHDR"u8)
            && BinaryPrimitives.ReadUInt32BigEndian(data.Slice(8, 4)) == 13)
        {
            return "image/png";
        }

        if (data.Length >= 4
            && data[0] == 0xFF
            && data[1] == 0xD8
            && data[2] == 0xFF)
        {
            return "image/jpeg";
        }

        if (data.Length >= 12
            && data[..4].SequenceEqual("RIFF"u8)
            && data.Slice(8, 4).SequenceEqual("WEBP"u8)
            && BinaryPrimitives.ReadUInt32LittleEndian(data.Slice(4, 4)) >= 4)
        {
            return "image/webp";
        }

        if (data.Length >= 13
            && (data[..6].SequenceEqual("GIF87a"u8) || data[..6].SequenceEqual("GIF89a"u8)))
        {
            return "image/gif";
        }

        if (data.Length >= 26 && data[..2].SequenceEqual("BM"u8))
        {
            return "image/bmp";
        }

        if (data.Length >= 8
            && (data[..4].SequenceEqual(new byte[] { 0x49, 0x49, 0x2A, 0x00 })
                || data[..4].SequenceEqual(new byte[] { 0x4D, 0x4D, 0x00, 0x2A })))
        {
            return "image/tiff";
        }

        throw new InvalidOperationException("Invalid or unsupported image format.");
    }
}